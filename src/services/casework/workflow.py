"""Durable workflow foundation for v2 intake, evidence, and independent review.

This module deliberately does not start a runner or expose HTTP routes.  It owns the
transactional casework state which route and worker layers can call without turning a
retry into a second clinical work item.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from src.services.casework.models import (
    CaseworkCommand,
    CaseworkRun,
    CaseworkWorkflow,
    Clarification,
    EditorDraft,
    IdempotencyRecord,
    InputRevision,
    OutputBasis,
    ProfessionalResponse,
    ReviewBasis,
    WorkItem,
)
from src.services.casework.store import etag_for, new_id
from src.services.errors import idempotency_conflict, invalid_request, invalid_state, not_found, version_conflict
from src.services.warehouse.db import session_scope
from src.services.warehouse.models import now

INPUT_KINDS = frozenset({"di", "adr"})
FIELD_STATUSES = frozenset({"proposed", "confirmed", "unknown"})
CLARIFICATION_CLASSIFICATIONS = frozenset({"required_for_next_step", "useful_for_completeness"})
RUN_PURPOSES = frozenset({"extraction", "preliminary_retrieval", "scoped_analysis"})
ADR_GROUPS = (
    "identifiable_patient",
    "identifiable_reporter",
    "suspected_medicinal_product",
    "suspected_adverse_reaction",
)
ADR_GROUP_STATUSES = frozenset({"present", "missing", "unknown"})
ADR_REPORTABILITY = frozenset({"not_assessed", "needs_information", "reportable", "not_reportable"})
WORK_TRANSITIONS = {
    "draft": {"accepted", "cancelled"},
    "accepted": {"in_progress", "awaiting_information", "cancelled"},
    "in_progress": {"awaiting_information", "awaiting_review", "cancelled"},
    "awaiting_information": {"in_progress", "cancelled"},
    "awaiting_review": {"in_progress", "awaiting_information", "completed", "cancelled"},
    # A material supplement opens the same completed WorkItem again.
    "completed": {"in_progress"},
    "cancelled": set(),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _actor_id(actor: dict[str, Any]) -> str:
    value = actor.get("id", actor.get("actor_id")) if isinstance(actor, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise invalid_request("actor.id không được để trống.")
    return value.strip()


def _actor(actor: dict[str, Any]) -> dict[str, Any]:
    actor_id = _actor_id(actor)
    result = {"id": actor_id}
    if actor.get("role") is not None:
        result["role"] = actor["role"]
    if actor.get("unit") is not None:
        result["unit"] = actor["unit"]
    return result


def _utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


def _source(source_id: str, version: int, kind: str, text: str, actor: dict[str, Any]) -> dict[str, Any]:
    if kind not in {"raw_question", "clarification_answer", "manual_correction"}:
        raise invalid_request("Loại InputSource không hợp lệ.")
    if not isinstance(text, str) or not text.strip():
        raise invalid_request("InputSource.text không được để trống.")
    return {
        "source_id": source_id,
        "source_version": version,
        "kind": kind,
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "actor": _actor(actor),
        "created_at": _utc(now()),
    }


def validate_assertions(assertions: list[dict[str, Any]], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate Unicode-code-point spans before writing an immutable revision."""
    source_text = {item["source_id"]: item["text"] for item in sources}
    checked: list[dict[str, Any]] = []
    for number, item in enumerate(assertions):
        if not isinstance(item, dict) or not isinstance(item.get("field_key"), str) or not item["field_key"].strip():
            raise invalid_request("FieldAssertion.field_key không được để trống.", {"index": number})
        status = item.get("status", "proposed")
        if status not in FIELD_STATUSES:
            raise invalid_request("FieldAssertion.status không hợp lệ.", {"index": number})
        if status == "unknown" and not isinstance(item.get("unknown_reason"), str):
            raise invalid_request("FieldAssertion unknown phải có unknown_reason.", {"index": number})
        spans = item.get("source_spans", [])
        if not isinstance(spans, list) or (status != "unknown" and not spans):
            raise invalid_request("FieldAssertion phải có source_spans, trừ unknown.", {"index": number})
        for span in spans:
            text = source_text.get(span.get("source_id")) if isinstance(span, dict) else None
            start = span.get("start") if isinstance(span, dict) else None
            end = span.get("end") if isinstance(span, dict) else None
            quote = span.get("quote") if isinstance(span, dict) else None
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
            ):
                raise invalid_request("Source span offsets phải là số nguyên Unicode code point.")
            if text is None or start < 0 or end < start or end > len(text) or text[start:end] != quote:
                raise invalid_request("Source span không khớp nguyên văn nguồn.")
        checked.append(dict(item))
    return checked


def adr_minimum_four(facts: dict[str, Any] | None) -> dict[str, Any]:
    facts = facts or {}
    groups: dict[str, dict[str, Any]] = {}
    states: list[str] = []
    for name in ADR_GROUPS:
        value = facts.get(name, {})
        if not isinstance(value, dict):
            value = {}
        status = value.get("status", "missing")
        if status not in ADR_GROUP_STATUSES:
            raise invalid_request("ADR minimum-four status không hợp lệ.", {"group": name})
        groups[name] = {
            "status": status,
            "assertion_refs": value.get("assertion_refs", []),
            "confirmed_by": value.get("confirmed_by"),
        }
        states.append(status)
    validity = (
        "complete"
        if all(value == "present" for value in states)
        else "undetermined"
        if "unknown" in states
        else "incomplete"
    )
    return {"groups": groups, "validity": validity}


class CaseWorkflowService:
    """Casework mutations with one transaction per clinical intent."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def _idempotent(self, session, actor: dict[str, Any], route: str, key: str | None, body: dict[str, Any], create):
        if not key:
            return create()
        actor_id = _actor_id(actor)
        request_hash = _hash(body)
        existing = session.execute(
            select(IdempotencyRecord).where(
                IdempotencyRecord.actor_id == actor_id,
                IdempotencyRecord.route == route,
                IdempotencyRecord.idempotency_key == key,
            )
        ).scalar_one_or_none()
        if existing:
            if existing.request_hash != request_hash:
                raise idempotency_conflict(key)
            return existing.response_json
        # The savepoint turns a same-key insert race into a deterministic replay rather
        # than poisoning the outer transaction or leaking a database 500.
        try:
            with session.begin_nested():
                response = create()
                session.add(
                    IdempotencyRecord(
                        actor_id=actor_id,
                        route=route,
                        idempotency_key=key,
                        request_hash=request_hash,
                        response_json=response,
                    )
                )
                session.flush()
                return response
        except IntegrityError:
            existing = session.execute(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.actor_id == actor_id,
                    IdempotencyRecord.route == route,
                    IdempotencyRecord.idempotency_key == key,
                )
            ).scalar_one_or_none()
            if existing is None or existing.request_hash != request_hash:
                raise idempotency_conflict(key)
            return existing.response_json

    def mutate(self, *, actor: dict[str, Any], route: str, idempotency_key: str, body: dict[str, Any], create):
        """Execute one route mutation and durable replay record in one transaction."""
        with session_scope(self.engine) as session:
            return self._idempotent(session, _actor(actor), route, idempotency_key, body, lambda: create(session))

    def create_intake(
        self,
        *,
        kind: str,
        raw_text: str,
        actor: dict[str, Any],
        language: str | None = None,
        priority: str = "routine",
        adr_facts: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if kind not in INPUT_KINDS or not isinstance(raw_text, str) or not raw_text.strip():
            raise invalid_request("kind phải là di|adr và raw_text không được để trống.")
        if priority not in {"routine", "urgent", "stat"}:
            raise invalid_request("priority không hợp lệ.")
        normalized_actor = _actor(actor)
        body = {"kind": kind, "raw_text": raw_text, "language": language, "priority": priority, "adr_facts": adr_facts}
        with session_scope(self.engine) as session:

            def create():
                work_item_id = new_id("wi")
                source = _source(new_id("src"), 1, "raw_question", raw_text, normalized_actor)
                adr = adr_minimum_four(adr_facts) if kind == "adr" else None
                revision = InputRevision(
                    input_revision_id=new_id("inrev"),
                    work_item_id=work_item_id,
                    revision=1,
                    sources_json=[source],
                    assertions_json=[],
                    adr_facts_json=adr,
                    content_hash=_hash({"sources": [source], "adr": adr}),
                    created_by_json=normalized_actor,
                )
                work = WorkItem(
                    work_item_id=work_item_id,
                    version=1,
                    etag=etag_for("work_item", work_item_id, 1),
                    context_json={"requester": normalized_actor, "language": language},
                    question=raw_text,
                    scope_json={},
                    unknowns_json=[],
                    priority=priority,
                    work_status="accepted",
                    run_status="queued",
                    review_status="not_required",
                    created_by_json=normalized_actor,
                )
                workflow = CaseworkWorkflow(
                    work_item_id=work_item_id,
                    kind=kind,
                    input_revision=1,
                    readiness_json=self._readiness([], kind),
                    adr_intake_json=self._adr_document(adr),
                )
                command_id = new_id("cmd")
                command = CaseworkCommand(
                    command_id=command_id,
                    work_item_id=work_item_id,
                    command_type="extract_fields",
                    operation_key=f"intake:{work_item_id}:1",
                    payload_json={"input_revision": 1},
                )
                session.add_all([work, workflow, revision, command])
                return {
                    "work_item_id": work_item_id,
                    "version": 1,
                    "input_revision": 1,
                    "operation_id": command.command_id,
                    "adr": self._adr_document(adr),
                }

            return self._idempotent(
                session, normalized_actor, "/api/v2/work-items/intake", idempotency_key, body, create
            )

    def _workflow(self, session, work_item_id: str) -> CaseworkWorkflow:
        row = session.get(CaseworkWorkflow, work_item_id)
        if row is None:
            raise not_found("workflow", work_item_id)
        return row

    def _readiness(self, assertions: list[dict[str, Any]], kind: str) -> dict[str, Any]:
        confirmed = {item.get("field_key") for item in assertions if item.get("status") == "confirmed"}
        blockers = (
            []
            if kind == "adr" or confirmed & {"drug", "purpose", "event_outcome"}
            else ["Cần xác nhận drug, purpose hoặc event/outcome trước scoped analysis."]
        )
        return {
            "can_retrieve_preliminary": bool(confirmed or kind == "adr"),
            "can_run_scoped_analysis": not blockers,
            "can_draft_limited": True,
            "can_submit_review": False,
            "blockers": blockers,
            "warnings": [],
            "policy_version": "workflow-v1",
        }

    def _adr_document(self, adr: dict[str, Any] | None) -> dict[str, Any] | None:
        if adr is None:
            return None
        return {
            **adr,
            "reportability": {
                "status": "not_assessed",
                "basis_input_revision": None,
                "assessor": None,
                "reason": None,
                "policy_reference": None,
            },
        }

    def _invalidate(self, session, work_item_id: str, reason: str) -> None:
        bases = (
            session.execute(
                select(OutputBasis).where(OutputBasis.work_item_id == work_item_id, OutputBasis.valid.is_(True))
            )
            .scalars()
            .all()
        )
        for basis in bases:
            basis.valid = False
            basis.invalidated_reason = reason
            session.execute(
                update(ReviewBasis)
                .where(ReviewBasis.basis_id == basis.basis_id, ReviewBasis.stale_reason.is_(None))
                .values(stale_reason=reason)
            )

    def update_fields(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        actor: dict[str, Any],
        assertions: list[dict[str, Any]],
        source_text: str | None = None,
    ) -> dict[str, Any]:
        actor = _actor(actor)
        with session_scope(self.engine) as session:
            work = session.get(WorkItem, work_item_id)
            workflow = self._workflow(session, work_item_id)
            if work is None:
                raise not_found("yêu cầu", work_item_id)
            if work.version != expected_version:
                raise version_conflict(expected_version, work.version)
            previous = session.execute(
                select(InputRevision).where(
                    InputRevision.work_item_id == work_item_id, InputRevision.revision == workflow.input_revision
                )
            ).scalar_one()
            sources = list(previous.sources_json or [])
            assertions = [dict(item) for item in assertions]
            # A correction is new human input; attach a real source and exact span rather
            # than relabelling the old extraction quote as if it said the new value.
            for assertion in assertions:
                correction = assertion.pop("manual_correction", None)
                if correction is not None:
                    source = _source(new_id("src"), len(sources) + 1, "manual_correction", str(correction), actor)
                    sources.append(source)
                    assertion["source_spans"] = [
                        {
                            "source_id": source["source_id"],
                            "start": 0,
                            "end": len(source["text"]),
                            "quote": source["text"],
                        }
                    ]
            if source_text is not None:
                sources.append(_source(new_id("src"), len(sources) + 1, "manual_correction", source_text, actor))
            checked = validate_assertions(assertions, sources)
            previous_by_id = {
                item.get("assertion_id"): item for item in previous.assertions_json or [] if item.get("assertion_id")
            }
            materialized = []
            for item in checked:
                assertion = dict(item)
                prior = previous_by_id.get(assertion.get("assertion_id"))
                assertion["assertion_id"] = assertion.get("assertion_id") or new_id("assert")
                changed = prior is None or _canonical(
                    {k: v for k, v in assertion.items() if k not in {"version", "confirmed_by", "confirmed_at"}}
                ) != _canonical(
                    {k: v for k, v in prior.items() if k not in {"version", "confirmed_by", "confirmed_at"}}
                )
                assertion["version"] = (
                    int(prior.get("version", 0)) + 1
                    if changed and prior
                    else int(prior.get("version", 1))
                    if prior
                    else int(assertion.get("version", 1))
                )
                if assertion.get("status") == "confirmed":
                    assertion["confirmed_by"] = actor
                    assertion["confirmed_at"] = _utc(now())
                materialized.append(assertion)
            confirmed = {
                item["field_key"]: item for item in previous.assertions_json or [] if item.get("status") == "confirmed"
            }
            merged = [
                item
                for item in materialized
                if not (item.get("status") == "proposed" and item.get("field_key") in confirmed)
            ]
            # A model proposal cannot replace a human confirmation, even on rerun.
            known = {item.get("field_key") for item in merged}
            merged.extend(value for key, value in confirmed.items() if key not in known)
            revision_number = workflow.input_revision + 1
            revision = InputRevision(
                input_revision_id=new_id("inrev"),
                work_item_id=work_item_id,
                revision=revision_number,
                sources_json=sources,
                assertions_json=merged,
                adr_facts_json=previous.adr_facts_json,
                content_hash=_hash({"sources": sources, "assertions": merged, "adr": previous.adr_facts_json}),
                created_by_json=actor,
            )
            result = session.execute(
                update(WorkItem)
                .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected_version)
                .values(
                    version=expected_version + 1,
                    etag=etag_for("work_item", work_item_id, expected_version + 1),
                    review_status="pending",
                    work_status="in_progress" if work.work_status == "completed" else work.work_status,
                    updated_at=now(),
                )
            )
            if result.rowcount != 1:
                raise version_conflict(expected_version, work.version)
            workflow.input_revision = revision_number
            workflow.readiness_json = self._readiness(merged, workflow.kind)
            workflow.updated_at = now()
            self._invalidate(session, work_item_id, "material_field_change")
            session.add(revision)
            return {
                "work_item_id": work_item_id,
                "version": expected_version + 1,
                "input_revision": revision_number,
                "field_assertions": merged,
                "readiness": workflow.readiness_json,
            }

    def transition_work_state(self, *, work_item_id: str, expected_version: int, target: str) -> dict[str, Any]:
        """Apply the workflow state machine with the same business CAS token."""
        with session_scope(self.engine) as session:
            work = session.get(WorkItem, work_item_id)
            self._workflow(session, work_item_id)
            if work is None:
                raise not_found("yêu cầu", work_item_id)
            if work.version != expected_version:
                raise version_conflict(expected_version, work.version)
            if target not in WORK_TRANSITIONS.get(work.work_status, set()):
                raise invalid_state("Work status transition không hợp lệ.", {"from": work.work_status, "to": target})
            result = session.execute(
                update(WorkItem)
                .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected_version)
                .values(
                    work_status=target,
                    version=expected_version + 1,
                    etag=etag_for("work_item", work_item_id, expected_version + 1),
                    updated_at=now(),
                )
            )
            if result.rowcount != 1:
                raise version_conflict(expected_version, work.version)
            return {"work_item_id": work_item_id, "work_status": target, "version": expected_version + 1}

    def create_clarification(
        self,
        *,
        work_item_id: str,
        field_key: str,
        question: str,
        classification: str,
        semantic_key: str,
        actor: dict[str, Any],
        blocked_step: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        if (
            classification not in CLARIFICATION_CLASSIFICATIONS
            or not field_key
            or not question.strip()
            or not semantic_key
        ):
            raise invalid_request("Clarification không hợp lệ.")
        with session_scope(self.engine) as session:
            workflow = self._workflow(session, work_item_id)
            existing = session.execute(
                select(Clarification).where(
                    Clarification.work_item_id == work_item_id,
                    Clarification.semantic_key == semantic_key,
                    Clarification.status == "open",
                )
            ).scalar_one_or_none()
            if existing:
                return self._clarification_document(existing)
            row = Clarification(
                clarification_id=new_id("clar"),
                work_item_id=work_item_id,
                field_key=field_key,
                question=question,
                classification=classification,
                blocked_step=blocked_step,
                reason=reason,
                input_revision=workflow.input_revision,
                semantic_key=semantic_key,
            )
            session.add(row)
            return self._clarification_document(row)

    def answer_clarification(
        self,
        *,
        work_item_id: str,
        clarification_id: str,
        expected_version: int,
        actor: dict[str, Any],
        answer: str | None,
        unknown: bool = False,
    ) -> dict[str, Any]:
        if unknown == (isinstance(answer, str) and bool(answer.strip())):
            raise invalid_request("Cần đúng một trong answer hoặc unknown.")
        actor = _actor(actor)
        with session_scope(self.engine) as session:
            work = session.get(WorkItem, work_item_id)
            workflow = self._workflow(session, work_item_id)
            row = session.get(Clarification, clarification_id)
            if work is None or row is None or row.work_item_id != work_item_id:
                raise not_found("clarification", clarification_id)
            if work.version != expected_version:
                raise version_conflict(expected_version, work.version)
            if row.status != "open":
                raise invalid_state("Clarification đã được đóng.")
            previous = session.execute(
                select(InputRevision).where(
                    InputRevision.work_item_id == work_item_id, InputRevision.revision == workflow.input_revision
                )
            ).scalar_one()
            sources = list(previous.sources_json or [])
            answer_source = (
                None
                if unknown
                else _source(new_id("src"), workflow.input_revision + 1, "clarification_answer", answer or "", actor)
            )
            if answer_source:
                sources.append(answer_source)
            row.status = "unknown" if unknown else "answered"
            row.answered_by_json = actor
            row.answered_at = now()
            row.answer_source_json = answer_source
            revision_number = workflow.input_revision + 1
            session.add(
                InputRevision(
                    input_revision_id=new_id("inrev"),
                    work_item_id=work_item_id,
                    revision=revision_number,
                    sources_json=sources,
                    assertions_json=previous.assertions_json or [],
                    adr_facts_json=previous.adr_facts_json,
                    content_hash=_hash(
                        {
                            "sources": sources,
                            "assertions": previous.assertions_json or [],
                            "adr": previous.adr_facts_json,
                        }
                    ),
                    created_by_json=actor,
                )
            )
            result = session.execute(
                update(WorkItem)
                .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected_version)
                .values(
                    version=expected_version + 1,
                    etag=etag_for("work_item", work_item_id, expected_version + 1),
                    updated_at=now(),
                )
            )
            if result.rowcount != 1:
                raise version_conflict(expected_version, work.version)
            workflow.input_revision, workflow.readiness_json, workflow.updated_at = (
                revision_number,
                self._readiness(previous.assertions_json or [], workflow.kind),
                now(),
            )
            self._invalidate(session, work_item_id, "clarification_answer")
            return {
                **self._clarification_document(row),
                "version": expected_version + 1,
                "input_revision": revision_number,
            }

    def create_run(
        self,
        *,
        work_item_id: str,
        purpose: str,
        actor: dict[str, Any],
        expected_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if purpose not in RUN_PURPOSES:
            raise invalid_request("Run purpose không hợp lệ.")
        actor = _actor(actor)
        with session_scope(self.engine) as session:

            def create():
                workflow = self._workflow(session, work_item_id)
                work = session.get(WorkItem, work_item_id)
                if work is None:
                    raise not_found("work_item", work_item_id)
                if expected_version is not None and work.version != expected_version:
                    raise version_conflict(expected_version, work.version)
                revision = session.execute(
                    select(InputRevision).where(
                        InputRevision.work_item_id == work_item_id, InputRevision.revision == workflow.input_revision
                    )
                ).scalar_one()
                if purpose == "scoped_analysis" and not workflow.readiness_json.get("can_run_scoped_analysis"):
                    raise invalid_state("Chưa đủ readiness để chạy scoped analysis.", workflow.readiness_json)
                if purpose == "preliminary_retrieval" and not workflow.readiness_json.get("can_retrieve_preliminary"):
                    raise invalid_state("Chưa đủ readiness để chạy preliminary retrieval.", workflow.readiness_json)
                run = CaseworkRun(
                    run_id=new_id("run"),
                    work_item_id=work_item_id,
                    purpose=purpose,
                    input_revision=workflow.input_revision,
                    input_hash=revision.content_hash,
                )
                command_id = new_id("cmd")
                command = CaseworkCommand(
                    command_id=command_id,
                    work_item_id=work_item_id,
                    run_id=run.run_id,
                    command_type=purpose,
                    operation_key=f"{purpose}:{work_item_id}:{workflow.input_revision}:{command_id}",
                    payload_json={
                        "input_revision": workflow.input_revision,
                        "input_hash": revision.content_hash,
                        "run_id": run.run_id,
                        "run_revision": 1,
                    },
                )
                workflow.current_run_id = run.run_id
                session.add_all([run, command])
                return {
                    "run_id": run.run_id,
                    "operation_id": command.command_id,
                    "state": "queued",
                    "input_revision": workflow.input_revision,
                }

            return self._idempotent(
                session,
                actor,
                f"/api/v2/work-items/{work_item_id}/runs",
                idempotency_key,
                {"purpose": purpose, "expected_version": expected_version},
                create,
            )

    def save_editor_draft(
        self,
        *,
        work_item_id: str,
        actor: dict[str, Any],
        entity: str,
        entity_id: str,
        base_versions: dict[str, int],
        content: dict[str, Any],
        expected_saved_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor_id = _actor_id(actor)
        with session_scope(self.engine) as session:

            def create() -> dict[str, Any]:
                self._workflow(session, work_item_id)
                row = session.execute(
                    select(EditorDraft).where(
                        EditorDraft.actor_id == actor_id,
                        EditorDraft.entity == entity,
                        EditorDraft.entity_id == entity_id,
                    )
                ).scalar_one_or_none()
                if row is None:
                    if expected_saved_version not in {None, 0}:
                        raise version_conflict(expected_saved_version, 0)
                    row = EditorDraft(
                        draft_id=new_id("draft"),
                        actor_id=actor_id,
                        entity=entity,
                        entity_id=entity_id,
                        base_versions_json=base_versions,
                        content_json=content,
                        saved_version=1,
                        updated_at=now(),
                    )
                    session.add(row)
                else:
                    if expected_saved_version is not None and row.saved_version != expected_saved_version:
                        raise version_conflict(expected_saved_version, row.saved_version)
                    row.base_versions_json = base_versions
                    row.content_json = content
                    row.saved_version += 1
                    row.updated_at = now()
                return {
                    "draft_id": row.draft_id,
                    "entity_type": entity,
                    "entity_id": entity_id,
                    "actor_id": actor_id,
                    "version": row.saved_version,
                    "base_versions": base_versions,
                    "content": content,
                    "saved_at": _utc(row.updated_at),
                }

            return self._idempotent(
                session,
                actor,
                f"/api/v2/work-items/{work_item_id}/editor-draft",
                idempotency_key,
                {
                    "entity": entity,
                    "entity_id": entity_id,
                    "base_versions": base_versions,
                    "content": content,
                    "expected_saved_version": expected_saved_version,
                },
                create,
            )

    def get_editor_draft(self, *, actor: dict[str, Any], entity: str, entity_id: str) -> dict[str, Any] | None:
        with session_scope(self.engine) as session:
            row = session.execute(
                select(EditorDraft).where(
                    EditorDraft.actor_id == _actor_id(actor),
                    EditorDraft.entity == entity,
                    EditorDraft.entity_id == entity_id,
                )
            ).scalar_one_or_none()
            return (
                None
                if row is None
                else {
                    "draft_id": row.draft_id,
                    "entity_type": entity,
                    "entity_id": entity_id,
                    "actor_id": row.actor_id,
                    "version": row.saved_version,
                    "base_versions": row.base_versions_json,
                    "content": row.content_json,
                    "saved_at": _utc(row.updated_at),
                }
            )

    def create_output_basis(
        self,
        *,
        work_item_id: str,
        response_id: str,
        response_version: int,
        basis: dict[str, Any],
        author_ids: list[str],
    ) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            workflow = self._workflow(session, work_item_id)
            if basis.get("input_revision") != workflow.input_revision:
                raise invalid_state("Output basis phải pin input revision hiện hành.")
            response = session.get(ProfessionalResponse, response_id)
            if response is not None and (response.work_item_id != work_item_id or response.version != response_version):
                raise invalid_state("Response không khớp output basis.")
            immutable = {
                **basis,
                "input_revision": workflow.input_revision,
                "response_id": response_id,
                "response_version": response_version,
            }
            row = OutputBasis(
                basis_id=new_id("basis"),
                work_item_id=work_item_id,
                response_id=response_id,
                response_version=response_version,
                basis_hash=_hash(immutable),
                input_revision=workflow.input_revision,
                basis_json=immutable,
                author_ids_json=sorted(set(author_ids)),
            )
            workflow.current_response_id = response_id
            session.add(row)
            return {
                "basis_id": row.basis_id,
                "basis_hash": row.basis_hash,
                "valid": True,
                "author_ids": row.author_ids_json,
            }

    def decide_review(
        self,
        *,
        work_item_id: str,
        basis_hash: str,
        response_id: str | None = None,
        reviewer: dict[str, Any],
        decision: str,
        expected_version: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if decision not in {"approved", "rejected", "changes_requested"}:
            raise invalid_request("Review decision không hợp lệ.")
        reviewer = _actor(reviewer)
        with session_scope(self.engine) as session:

            def create() -> dict[str, Any]:
                work = session.get(WorkItem, work_item_id)
                if work is None:
                    raise not_found("yêu cầu", work_item_id)
                if work.version != expected_version:
                    raise version_conflict(expected_version, work.version)
                basis = session.execute(
                    select(OutputBasis).where(
                        OutputBasis.work_item_id == work_item_id, OutputBasis.basis_hash == basis_hash
                    )
                ).scalar_one_or_none()
                if basis is None or not basis.valid:
                    raise invalid_state("Basis không còn hiệu lực để duyệt.")
                if response_id is not None and basis.response_id != response_id:
                    raise invalid_state("URL response_id không khớp basis.")
                response = session.get(ProfessionalResponse, basis.response_id)
                workflow = self._workflow(session, work_item_id)
                if (
                    response is None
                    or workflow.current_response_id != basis.response_id
                    or response.version != basis.response_version
                    or response.status != "in_review"
                    or basis.input_revision != workflow.input_revision
                    or work.work_status != "awaiting_review"
                ):
                    raise invalid_state("Chỉ current response đang in_review với basis current được duyệt.")
                if reviewer["id"] in set(basis.author_ids_json or []):
                    raise invalid_state("Người soạn hoặc sửa nội dung quan trọng không được tự duyệt.")
                session.add(
                    ReviewBasis(
                        review_basis_id=new_id("reviewbasis"),
                        basis_id=basis.basis_id,
                        work_item_id=work_item_id,
                        reviewer_json=reviewer,
                        decision=decision,
                    )
                )
                result = session.execute(
                    update(WorkItem)
                    .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected_version)
                    .values(
                        version=expected_version + 1,
                        etag=etag_for("work_item", work_item_id, expected_version + 1),
                        review_status=decision,
                        work_status="completed" if decision == "approved" else "awaiting_review",
                        updated_at=now(),
                    )
                )
                if result.rowcount != 1:
                    raise version_conflict(expected_version, work.version)
                response.status = (
                    "approved" if decision == "approved" else "rejected" if decision == "rejected" else "draft"
                )
                response.approval_json = {
                    "decision": decision,
                    "reviewer": reviewer,
                    "basis_hash": basis_hash,
                    "decided_at": _utc(now()),
                }
                response.updated_at = now()
                return {"basis_hash": basis_hash, "decision": decision, "version": expected_version + 1}

            return self._idempotent(
                session,
                reviewer,
                f"/api/v2/work-items/{work_item_id}/review",
                idempotency_key,
                {
                    "basis_hash": basis_hash,
                    "decision": decision,
                    "expected_version": expected_version,
                },
                create,
            )

    def set_adr_reportability(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        status: str,
        assessor: dict[str, Any] | None,
        reason: str | None,
        policy_reference: str | None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if status not in ADR_REPORTABILITY:
            raise invalid_request("ADR reportability không hợp lệ.")
        with session_scope(self.engine) as session:

            def create():
                workflow, work = self._workflow(session, work_item_id), session.get(WorkItem, work_item_id)
                if workflow.kind != "adr":
                    raise invalid_state("Chỉ ADR có reportability.")
                if work is None or work.version != expected_version:
                    raise version_conflict(expected_version, work.version if work else 0)
                intake = dict(workflow.adr_intake_json or {})
                intake["reportability"] = {
                    "status": status,
                    "basis_input_revision": workflow.input_revision,
                    "assessor": _actor(assessor) if assessor else None,
                    "reason": reason,
                    "policy_reference": policy_reference,
                }
                result = session.execute(
                    update(WorkItem)
                    .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected_version)
                    .values(
                        version=expected_version + 1,
                        etag=etag_for("work_item", work_item_id, expected_version + 1),
                        updated_at=now(),
                    )
                )
                if result.rowcount != 1:
                    raise version_conflict(expected_version, work.version)
                workflow.adr_intake_json, workflow.updated_at = intake, now()
                return intake["reportability"] | {"version": expected_version + 1}

            return self._idempotent(
                session,
                _actor(assessor),
                f"/api/v2/work-items/{work_item_id}/adr-reportability",
                idempotency_key,
                {
                    "expected_version": expected_version,
                    "status": status,
                    "reason": reason,
                    "policy_reference": policy_reference,
                },
                create,
            )

    def patch_adr(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        actor: dict[str, Any],
        patch: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        actor = _actor(actor)
        if "reportability" in patch or "confirmed_by" in _canonical(patch):
            raise invalid_request("ADR patch không được ghi reportability hoặc confirmed_by.")

        def create(session):
            work, flow = session.get(WorkItem, work_item_id), self._workflow(session, work_item_id)
            if work is None or flow.kind != "adr":
                raise invalid_state("Chỉ ADR có adr-intake.")
            if work.version != expected_version:
                raise version_conflict(expected_version, work.version)
            prior = session.execute(
                select(InputRevision).where(
                    InputRevision.work_item_id == work_item_id, InputRevision.revision == flow.input_revision
                )
            ).scalar_one()
            current = dict(flow.adr_intake_json or {})
            current.update(patch)
            facts = current.get("groups") or current.get("minimum_four") or {}
            adr = adr_minimum_four(facts if isinstance(facts, dict) else {})
            intake = {
                **current,
                **adr,
                "reportability": {
                    "status": "not_assessed",
                    "basis_input_revision": None,
                    "assessor": None,
                    "reason": None,
                    "policy_reference": None,
                },
            }
            revision = flow.input_revision + 1
            session.add(
                InputRevision(
                    input_revision_id=new_id("inrev"),
                    work_item_id=work_item_id,
                    revision=revision,
                    sources_json=prior.sources_json or [],
                    assertions_json=prior.assertions_json or [],
                    adr_facts_json=adr,
                    content_hash=_hash(
                        {"sources": prior.sources_json or [], "assertions": prior.assertions_json or [], "adr": adr}
                    ),
                    created_by_json=actor,
                )
            )
            result = session.execute(
                update(WorkItem)
                .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected_version)
                .values(
                    version=expected_version + 1,
                    etag=etag_for("work_item", work_item_id, expected_version + 1),
                    review_status="pending",
                    updated_at=now(),
                )
            )
            if result.rowcount != 1:
                raise version_conflict(expected_version, work.version)
            flow.input_revision, flow.adr_intake_json, flow.readiness_json, flow.updated_at = (
                revision,
                intake,
                self._readiness(prior.assertions_json or [], "adr"),
                now(),
            )
            self._invalidate(session, work_item_id, "adr_intake_change")
            return {"work_item_id": work_item_id, "version": expected_version + 1, "input_revision": revision}

        return self.mutate(
            actor=actor,
            route=f"/api/v2/work-items/{work_item_id}/adr-intake",
            idempotency_key=idempotency_key,
            body={"expected_version": expected_version, "patch": patch},
            create=create,
        )

    def save_response_with_basis(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        input_revision: int,
        sections: list[dict[str, Any]],
        bundle_id: str | None,
        actor: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        actor = _actor(actor)

        def create(session):
            work, flow = session.get(WorkItem, work_item_id), self._workflow(session, work_item_id)
            if work is None or work.version != expected_version:
                raise version_conflict(expected_version, work.version if work else 0)
            if flow.input_revision != input_revision:
                raise invalid_state("Input revision đã cũ.")
            old = session.get(ProfessionalResponse, flow.current_response_id) if flow.current_response_id else None
            if old:
                old.status, old.updated_at = "superseded", now()
            self._invalidate(session, work_item_id, "new_response")
            version = (
                int(
                    session.execute(
                        select(func.max(ProfessionalResponse.version)).where(
                            ProfessionalResponse.work_item_id == work_item_id
                        )
                    ).scalar()
                    or 0
                )
                + 1
            )
            response = ProfessionalResponse(
                response_id=new_id("resp"),
                work_item_id=work_item_id,
                version=version,
                etag=etag_for("response", work_item_id, version),
                status="draft",
                sections_json=sections,
                assessment_status="insufficient_evidence",
                coverage_json={"status": "not_requested"},
                drafted_by_json=actor,
                supersedes=old.response_id if old else None,
            )
            session.add(response)
            session.flush()
            immutable = {
                "input_revision": input_revision,
                "bundle_id": bundle_id,
                "response_content_hash": _hash(sections),
                "response_id": response.response_id,
                "response_version": version,
            }
            basis = OutputBasis(
                basis_id=new_id("basis"),
                work_item_id=work_item_id,
                response_id=response.response_id,
                response_version=version,
                basis_hash=_hash(immutable),
                input_revision=input_revision,
                basis_json=immutable,
                author_ids_json=[actor["id"]],
            )
            session.add(basis)
            result = session.execute(
                update(WorkItem)
                .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected_version)
                .values(
                    version=expected_version + 1,
                    etag=etag_for("work_item", work_item_id, expected_version + 1),
                    review_status="pending",
                    updated_at=now(),
                )
            )
            if result.rowcount != 1:
                raise version_conflict(expected_version, work.version)
            flow.current_response_id, flow.updated_at = response.response_id, now()
            return {
                "response_id": response.response_id,
                "version": version,
                "status": "draft",
                "basis_id": basis.basis_id,
                "basis_hash": basis.basis_hash,
                "author_ids": [actor["id"]],
            }

        return self.mutate(
            actor=actor,
            route=f"/api/v2/work-items/{work_item_id}/drafts",
            idempotency_key=idempotency_key,
            body={
                "expected_version": expected_version,
                "input_revision": input_revision,
                "sections": sections,
                "bundle_id": bundle_id,
            },
            create=create,
        )

    def submit_response(
        self,
        *,
        response_id: str,
        expected_response_version: int,
        expected_work_version: int,
        basis_hash: str,
        actor: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        actor = _actor(actor)

        def create(session):
            response = session.get(ProfessionalResponse, response_id)
            if response is None:
                raise not_found("response", response_id)
            flow, work = self._workflow(session, response.work_item_id), session.get(WorkItem, response.work_item_id)
            if (
                response_id != flow.current_response_id
                or response.version != expected_response_version
                or response.status != "draft"
            ):
                raise invalid_state("Chỉ response current ở draft được submit.")
            if work.version != expected_work_version or work.work_status not in {
                "accepted",
                "in_progress",
                "awaiting_information",
            }:
                raise invalid_state("Work không ở trạng thái cho phép submit.")
            basis = session.execute(
                select(OutputBasis).where(
                    OutputBasis.response_id == response_id,
                    OutputBasis.basis_hash == basis_hash,
                    OutputBasis.valid.is_(True),
                )
            ).scalar_one_or_none()
            if (
                basis is None
                or basis.input_revision != flow.input_revision
                or basis.response_version != response.version
            ):
                raise invalid_state("Basis không còn current/hợp lệ.")
            response.status, response.updated_at = "in_review", now()
            result = session.execute(
                update(WorkItem)
                .where(WorkItem.work_item_id == work.work_item_id, WorkItem.version == expected_work_version)
                .values(
                    version=expected_work_version + 1,
                    etag=etag_for("work_item", work.work_item_id, expected_work_version + 1),
                    review_status="pending",
                    work_status="awaiting_review",
                    updated_at=now(),
                )
            )
            if result.rowcount != 1:
                raise version_conflict(expected_work_version, work.version)
            return {
                "response_id": response_id,
                "status": "in_review",
                "basis_hash": basis_hash,
                "version": expected_work_version + 1,
            }

        return self.mutate(
            actor=actor,
            route=f"/api/v2/responses/{response_id}/submit-review",
            idempotency_key=idempotency_key,
            body={
                "response_version": expected_response_version,
                "work_version": expected_work_version,
                "basis_hash": basis_hash,
            },
            create=create,
        )

    def _clarification_document(self, row: Clarification) -> dict[str, Any]:
        return {
            "clarification_id": row.clarification_id,
            "work_item_id": row.work_item_id,
            "field_key": row.field_key,
            "question": row.question,
            "classification": row.classification,
            "blocked_step": row.blocked_step,
            "reason": row.reason,
            "status": row.status,
            "input_revision": row.input_revision,
            "semantic_key": row.semantic_key,
            "answer_source": row.answer_source_json,
            "answered_by": row.answered_by_json,
            "supersedes": row.supersedes,
            "created_at": _utc(row.created_at),
            "answered_at": _utc(row.answered_at),
        }
