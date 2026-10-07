"""Managed `/api/v2` workflow routes.

This router is intentionally a thin HTTP layer over ``CaseWorkflowService``.  Legacy
v2 work-item endpoints remain available for legacy records, but workflow-managed records
only publish, review, and export through the version-bound operations below.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

from src.api.auth import Principal, require_permission
from src.api.v2_routes import get_casework_store
from src.services.casework.models import (
    CaseworkCommand,
    CaseworkRun,
    CaseworkWorkflow,
    Clarification,
    FollowUp,
    InputRevision,
    OutputBasis,
    ProfessionalResponse,
    ReviewBasis,
    WorkItem,
)
from src.services.casework.store import CaseWorkStore, etag_for, new_id
from src.services.casework.workflow import CaseWorkflowService, adr_minimum_four
from src.services.errors import invalid_request, invalid_state, not_found, version_conflict
from src.services.identity import Permission
from src.services.warehouse.db import session_scope
from src.services.warehouse.models import now

router = APIRouter(tags=["workflow-v2"])
StoreDep = Annotated[CaseWorkStore, Depends(get_casework_store)]
ReadPrincipal = Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_READ_OWN))]
RunPrincipal = Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_RUN_OWN))]
CreatePrincipal = Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_CREATE))]
ReviewPrincipal = Annotated[Principal, Depends(require_permission(Permission.REVIEW_DECIDE))]


class IntakeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["di", "adr"]
    raw_text: str = Field(min_length=1, max_length=8000)
    language: str | None = Field(default=None, max_length=30)
    priority: Literal["routine", "urgent", "stat"] = "routine"
    adr_facts: dict[str, Any] | None = None


class FieldOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assertion_id: str = Field(min_length=1, max_length=80)
    expected_assertion_version: int = Field(ge=1)
    action: Literal["confirm", "correct", "mark_unknown"]
    value: str | None = Field(default=None, max_length=1000)
    reason: str | None = Field(default=None, max_length=500)


class FieldsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    operations: list[FieldOperation] = Field(min_length=1, max_length=50)


class ClarificationAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clarification_id: str
    expected_clarification_version: int = Field(ge=1)
    text: str | None = Field(default=None, max_length=4000)
    answer_state: Literal["answered", "unknown"]


class ClarificationAnswersIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    answers: list[ClarificationAnswer] = Field(min_length=1, max_length=20)


class RunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    purpose: Literal["extraction", "preliminary_retrieval", "preliminary", "scoped_analysis"]


class RunReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_work_version: int = Field(ge=1)
    action: Literal["approve", "request_changes"]
    reason: str | None = Field(default=None, max_length=1000)


class DraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    expected_input_revision: int = Field(ge=1)
    bundle_id: str | None = None
    previous_response_id: str | None = None
    sections: dict[str, str] = Field(default_factory=dict)


class EditorDraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_versions: dict[str, int]
    content: dict[str, Any]
    version: int | None = None


class SubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    expected_work_version: int = Field(ge=1)
    basis_hash: str = Field(min_length=64, max_length=64)


class ReviewIn(BaseModel):
    """Review shape accepts the legacy body only to preserve legacy response review.

    A managed response additionally requires its immutable workflow basis and work
    version; their absence can never downgrade a managed review to the legacy path.
    """

    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    expected_work_version: int | None = Field(default=None, ge=1)
    basis_hash: str | None = Field(default=None, min_length=64, max_length=64)
    action: Literal["approve", "approved", "reject", "rejected", "request_changes", "changes_requested"]
    reason: str | None = Field(default=None, max_length=2000)


class AdrPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    patch: dict[str, Any]
    reason: str | None = Field(default=None, max_length=500)


class ReportabilityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    status: Literal["not_assessed", "needs_information", "reportable", "not_reportable"]
    reason: str | None = Field(default=None, max_length=1000)
    policy_reference: str | None = Field(default=None, max_length=300)


class FollowUpPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    status: Literal["done", "cancelled"]
    resolution: str = Field(min_length=1, max_length=2000)


def _actor(principal: Principal) -> dict[str, str]:
    return {"id": principal.user_id, "role": str(principal.role)}


def _require_key(key: str | None) -> str:
    if not key or not key.strip():
        raise invalid_request("Mọi POST workflow mutation phải có Idempotency-Key.")
    return key.strip()


def _is_visible(work: WorkItem, principal: Principal) -> bool:
    if principal.has(Permission.INVESTIGATION_READ_ANY):
        return True
    ids = {
        (work.created_by_json or {}).get("id"),
        (work.owner_json or {}).get("id"),
        ((work.context_json or {}).get("requester") or {}).get("id"),
    }
    return principal.user_id in ids


def _work(store: CaseWorkStore, work_item_id: str, principal: Principal, *, write: bool = False) -> WorkItem:
    with session_scope(store.engine) as session:
        work = session.get(WorkItem, work_item_id)
        managed = session.get(CaseworkWorkflow, work_item_id)
        if work is None or managed is None or not _is_visible(work, principal):
            raise not_found("yêu cầu", work_item_id)
        if write and not (
            principal.has(Permission.INVESTIGATION_RUN_ANY)
            or (
                principal.has(Permission.INVESTIGATION_RUN_OWN)
                and principal.user_id in {(work.created_by_json or {}).get("id"), (work.owner_json or {}).get("id")}
            )
        ):
            raise not_found("yêu cầu", work_item_id)
        session.expunge(work)
        return work


def _response_for(
    store: CaseWorkStore, response_id: str, principal: Principal, *, write: bool = False
) -> tuple[ProfessionalResponse, WorkItem]:
    with session_scope(store.engine) as session:
        response = session.get(ProfessionalResponse, response_id)
        if response is None:
            raise not_found("response", response_id)
        work = session.get(WorkItem, response.work_item_id)
        if work is None or session.get(CaseworkWorkflow, work.work_item_id) is None or not _is_visible(work, principal):
            raise not_found("response", response_id)
        if write and not principal.has(Permission.REVIEW_DECIDE):
            raise not_found("response", response_id)
        session.expunge(response)
        session.expunge(work)
        return response, work


def _assert_match(header: str | None, expected: int) -> None:
    if header is None:
        return
    raw = header.strip().removeprefix("W/").strip('"')
    if raw.isdigit() and int(raw) != expected:
        raise invalid_request("If-Match và expected_version không nhất quán.")


def _run_doc(row: CaseworkRun) -> dict[str, Any]:
    return {
        "id": row.run_id,
        "run_id": row.run_id,
        "version": row.progress_revision,
        "purpose": row.purpose,
        "status": row.state,
        "state": row.state,
        "input_revision": row.input_revision,
        "source_results": row.source_results_json or [],
        "error": row.error_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _aggregate(store: CaseWorkStore, work_item_id: str, principal: Principal) -> dict[str, Any]:
    _work(store, work_item_id, principal)
    with session_scope(store.engine) as session:
        work = session.get(WorkItem, work_item_id)
        flow = session.get(CaseworkWorkflow, work_item_id)
        revision = session.execute(
            select(InputRevision).where(
                InputRevision.work_item_id == work_item_id, InputRevision.revision == flow.input_revision
            )
        ).scalar_one()
        clarifications = (
            session.execute(
                select(Clarification)
                .where(Clarification.work_item_id == work_item_id)
                .order_by(Clarification.created_at)
            )
            .scalars()
            .all()
        )
        runs = (
            session.execute(
                select(CaseworkRun).where(CaseworkRun.work_item_id == work_item_id).order_by(CaseworkRun.created_at)
            )
            .scalars()
            .all()
        )
        response = session.get(ProfessionalResponse, flow.current_response_id) if flow.current_response_id else None
        basis = (
            session.execute(
                select(OutputBasis)
                .where(OutputBasis.work_item_id == work_item_id, OutputBasis.valid.is_(True))
                .order_by(OutputBasis.created_at.desc())
            )
            .scalars()
            .first()
        )
        allowed = ["retrieve_preliminary", "save_editor_draft", "answer_clarification"]
        if flow.readiness_json.get("can_run_scoped_analysis"):
            allowed.append("run_scoped_analysis")
        if basis is not None:
            allowed.append("submit_review")
        return {
            "work_item": {
                "id": work.work_item_id,
                "work_item_id": work.work_item_id,
                "kind": flow.kind,
                "raw_text": work.question,
                "priority": work.priority,
                "version": work.version,
                "input_revision": flow.input_revision,
                "work_status": work.work_status,
                "run_status": work.run_status,
                "review_status": work.review_status,
                "created_at": work.created_at.isoformat() if work.created_at else None,
                "updated_at": work.updated_at.isoformat() if work.updated_at else None,
            },
            "input_sources": revision.sources_json or [],
            "field_assertions": revision.assertions_json or [],
            "clarifications": [
                {
                    "id": row.clarification_id,
                    "clarification_id": row.clarification_id,
                    "version": 1,
                    "field_keys": [row.field_key],
                    "question": row.question,
                    "classification": row.classification,
                    "blocked_step": row.blocked_step,
                    "reason": row.reason,
                    "status": row.status,
                    "based_on_input_revision": row.input_revision,
                    "dedupe_key": row.semantic_key,
                    "answer_source_id": (row.answer_source_json or {}).get("source_id"),
                    "answered_by": (row.answered_by_json or {}).get("id"),
                    "answered_at": row.answered_at.isoformat() if row.answered_at else None,
                }
                for row in clarifications
            ],
            "readiness": flow.readiness_json or {},
            "runs": [_run_doc(row) for row in runs],
            "current_response": None
            if response is None
            else {
                "response_id": response.response_id,
                "version": response.version,
                "status": response.status,
                "sections": {
                    item.get("key", str(index)): item.get("text", "")
                    for index, item in enumerate(response.sections_json or [])
                },
                "author_ids": ((basis.author_ids_json if basis else []) or []),
                "basis_hash": basis.basis_hash if basis else None,
                "updated_at": response.updated_at.isoformat() if response.updated_at else None,
            },
            "version_basis": None
            if basis is None
            else {
                "basis_hash": basis.basis_hash,
                "input_revision": basis.input_revision,
                "response_id": basis.response_id,
                "response_version": basis.response_version,
                "stale_reason": basis.invalidated_reason,
            },
            "adr_intake": flow.adr_intake_json,
            "allowed_actions": allowed,
            "aggregate_etag": etag_for("workflow", work_item_id, work.version),
        }


@router.post("/work-items/intake", status_code=201)
def intake(
    payload: IntakeIn,
    store: StoreDep,
    principal: CreatePrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    receipt = store.create_intake(
        kind=payload.kind,
        raw_text=payload.raw_text,
        actor=_actor(principal),
        language=payload.language,
        priority=payload.priority,
        adr_facts=payload.adr_facts,
        idempotency_key=_require_key(idempotency_key),
    )
    return _aggregate(store, receipt["work_item_id"], principal)["work_item"] | {
        "operation_id": receipt["operation_id"],
        "adr": receipt["adr"],
    }


@router.get("/work-items/{work_item_id}/workflow")
def workflow(work_item_id: str, store: StoreDep, principal: ReadPrincipal, response: Response) -> dict[str, Any]:
    document = _aggregate(store, work_item_id, principal)
    response.headers["ETag"] = document["aggregate_etag"]
    return document


@router.patch("/work-items/{work_item_id}/fields")
def fields(
    work_item_id: str,
    payload: FieldsIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    _assert_match(if_match, payload.expected_version)
    _work(store, work_item_id, principal, write=True)
    before = _aggregate(store, work_item_id, principal)
    assertions = [dict(item) for item in before["field_assertions"]]
    by_id = {item.get("assertion_id"): item for item in assertions}
    for op in payload.operations:
        assertion = by_id.get(op.assertion_id)
        if assertion is None or assertion.get("version") != op.expected_assertion_version:
            raise version_conflict(op.expected_assertion_version, int((assertion or {}).get("version", 0)))
        if op.action == "confirm":
            assertion["status"] = "confirmed"
        elif op.action == "mark_unknown":
            assertion.update(
                status="unknown", value=None, unknown_reason=op.reason or "Người dùng chưa biết", source_spans=[]
            )
        else:
            # A correction must retain existing source provenance; new free-text facts go
            # through a manual correction source rather than pretending the old quote said it.
            if op.value is None:
                raise invalid_request("correct cần value.")
            assertion["value"] = op.value
    store.update_fields(
        work_item_id=work_item_id,
        expected_version=payload.expected_version,
        actor=_actor(principal),
        assertions=assertions,
    )
    return _aggregate(store, work_item_id, principal)


@router.post("/work-items/{work_item_id}/clarification-answers")
def clarification_answers(
    work_item_id: str,
    payload: ClarificationAnswersIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    _work(store, work_item_id, principal, write=True)
    version = payload.expected_version
    for answer in payload.answers:
        if answer.expected_clarification_version != 1:
            raise version_conflict(answer.expected_clarification_version, 1)
        store.answer_clarification(
            work_item_id=work_item_id,
            clarification_id=answer.clarification_id,
            expected_version=version,
            actor=_actor(principal),
            answer=answer.text,
            unknown=answer.answer_state == "unknown",
        )
        version += 1
    return _aggregate(store, work_item_id, principal)


@router.post("/work-items/{work_item_id}/runs", status_code=202)
def start_run(
    work_item_id: str,
    payload: RunIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    work = _work(store, work_item_id, principal, write=True)
    if work.version != payload.expected_version:
        raise version_conflict(payload.expected_version, work.version)
    purpose = "preliminary_retrieval" if payload.purpose == "preliminary" else payload.purpose
    return store.create_casework_run(
        work_item_id=work_item_id, purpose=purpose, actor=_actor(principal), idempotency_key=idempotency_key
    )


@router.post("/work-items/{work_item_id}/runs/{run_id}/continue", status_code=202)
def continue_run(
    work_item_id: str,
    run_id: str,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    _work(store, work_item_id, principal, write=True)
    with session_scope(store.engine) as session:
        row = session.get(CaseworkRun, run_id)
        if row is None or row.work_item_id != work_item_id:
            raise not_found("run", run_id)
        if row.state in {"completed", "cancelled"}:
            raise invalid_state("Run đã kết thúc.")
        row.state = "queued"
        row.progress_revision += 1
        row.updated_at = now()
        cmd = CaseworkCommand(
            command_id=new_id("cmd"),
            work_item_id=work_item_id,
            run_id=run_id,
            command_type=row.purpose,
            operation_key=f"continue:{run_id}:{row.progress_revision}",
            payload_json={"run_id": run_id},
        )
        session.add(cmd)
        return {"run_id": run_id, "operation_id": cmd.command_id, "state": "queued"}


@router.post("/work-items/{work_item_id}/runs/{run_id}/cancel")
def cancel_run(
    work_item_id: str,
    run_id: str,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    _work(store, work_item_id, principal, write=True)
    with session_scope(store.engine) as session:
        row = session.get(CaseworkRun, run_id)
        if row is None or row.work_item_id != work_item_id:
            raise not_found("run", run_id)
        if row.state in {"completed", "failed", "cancelled"}:
            raise invalid_state("Run đã kết thúc.")
        row.state = "cancelled"
        row.progress_revision += 1
        row.updated_at = now()
        session.execute(
            update(CaseworkCommand)
            .where(CaseworkCommand.run_id == run_id, CaseworkCommand.state.in_(["queued", "running"]))
            .values(state="cancelled", updated_at=now())
        )
        return _run_doc(row)


@router.post("/work-items/{work_item_id}/runs/{run_id}/review")
def review_run(
    work_item_id: str,
    run_id: str,
    payload: RunReviewIn,
    store: StoreDep,
    principal: ReviewPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    """Record a human run checkpoint without treating it as response approval."""
    _require_key(idempotency_key)
    work = _work(store, work_item_id, principal)
    if work.version != payload.expected_work_version:
        raise version_conflict(payload.expected_work_version, work.version)
    with session_scope(store.engine) as session:
        row = session.get(CaseworkRun, run_id)
        if row is None or row.work_item_id != work_item_id:
            raise not_found("run", run_id)
        if row.state not in {"completed", "waiting_for_review"}:
            raise invalid_state("Run chưa sẵn sàng để review.")
        row.state, row.progress_revision, row.updated_at = (
            ("completed" if payload.action == "approve" else "waiting_for_review"),
            row.progress_revision + 1,
            now(),
        )
        row.error_json = (
            None if payload.action == "approve" else {"kind": "changes_requested", "reason": payload.reason}
        )
        return _run_doc(row)


@router.post("/work-items/{work_item_id}/drafts", status_code=201)
def create_draft(
    work_item_id: str,
    payload: DraftIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    work = _work(store, work_item_id, principal, write=True)
    if work.version != payload.expected_version:
        raise version_conflict(payload.expected_version, work.version)
    aggregate = _aggregate(store, work_item_id, principal)
    if aggregate["work_item"]["input_revision"] != payload.expected_input_revision:
        raise invalid_state("Input revision đã cũ.")
    sections = [
        {"key": key, "title": key, "text": text, "citations": []} for key, text in payload.sections.items() if text
    ]
    if not sections:
        sections = [{"key": "summary", "title": "Nháp", "text": "Chưa có nội dung lâm sàng.", "citations": []}]
    response = store.save_response(
        work_item_id=work_item_id,
        sections=sections,
        status="draft",
        assessment_status="insufficient_evidence",
        coverage={"status": "not_requested"},
        drafted_by=_actor(principal),
        actor=_actor(principal),
    )
    content_hash = hashlib.sha256(json.dumps(sections, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    basis = store.create_output_basis(
        work_item_id=work_item_id,
        response_id=response["response_id"],
        response_version=response["version"],
        basis={
            "input_revision": payload.expected_input_revision,
            "bundle_id": payload.bundle_id,
            "response_content_hash": content_hash,
            "source_results": aggregate["runs"],
        },
        author_ids=[principal.user_id],
    )
    return {
        "response_id": response["response_id"],
        "version": response["version"],
        "status": "draft",
        "sections": payload.sections,
        "author_ids": [principal.user_id],
        **basis,
    }


@router.get("/work-items/{work_item_id}/editor-draft")
def get_editor_draft(work_item_id: str, store: StoreDep, principal: ReadPrincipal) -> dict[str, Any] | None:
    _work(store, work_item_id, principal)
    return store.get_editor_draft(actor=_actor(principal), entity="work_item", entity_id=work_item_id)


@router.patch("/work-items/{work_item_id}/editor-draft")
def save_editor_draft(
    work_item_id: str,
    payload: EditorDraftIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    idempotency_key = _require_key(idempotency_key)
    _work(store, work_item_id, principal, write=True)
    return store.save_editor_draft(
        work_item_id=work_item_id,
        actor=_actor(principal),
        entity="work_item",
        entity_id=work_item_id,
        base_versions=payload.base_versions,
        content=payload.content,
        expected_saved_version=payload.version,
        idempotency_key=idempotency_key,
    )


@router.post("/responses/{response_id}/submit-review")
def submit_review(
    response_id: str,
    payload: SubmitIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    response, work = _response_for(store, response_id, principal)
    if response.version != payload.expected_version or work.version != payload.expected_work_version:
        raise version_conflict(payload.expected_work_version, work.version)
    with session_scope(store.engine) as session:
        basis = session.execute(
            select(OutputBasis).where(
                OutputBasis.response_id == response_id,
                OutputBasis.basis_hash == payload.basis_hash,
                OutputBasis.valid.is_(True),
            )
        ).scalar_one_or_none()
        if basis is None:
            raise invalid_state("Basis không còn hiệu lực.")
        session.execute(
            update(ProfessionalResponse)
            .where(
                ProfessionalResponse.response_id == response_id,
                ProfessionalResponse.version == payload.expected_version,
            )
            .values(status="in_review", updated_at=now())
        )
        session.execute(
            update(WorkItem)
            .where(WorkItem.work_item_id == work.work_item_id, WorkItem.version == payload.expected_work_version)
            .values(
                review_status="pending",
                work_status="awaiting_review",
                version=work.version + 1,
                etag=etag_for("work_item", work.work_item_id, work.version + 1),
                updated_at=now(),
            )
        )
    return {"response_id": response_id, "status": "in_review", "basis_hash": payload.basis_hash}


@router.get("/work-items/{work_item_id}/events")
def events(
    work_item_id: str, store: StoreDep, principal: ReadPrincipal, after_id: int = Query(default=0, ge=0)
) -> dict[str, Any]:
    _work(store, work_item_id, principal)
    with session_scope(store.engine) as session:
        commands = (
            session.execute(
                select(CaseworkCommand)
                .where(CaseworkCommand.work_item_id == work_item_id)
                .order_by(CaseworkCommand.created_at)
            )
            .scalars()
            .all()
        )
        records = [
            {
                "id": index + 1,
                "kind": "operation",
                "operation_id": row.command_id,
                "state": row.state,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for index, row in enumerate(commands)
        ]
        return {"events": [row for row in records if row["id"] > after_id]}


@router.get("/work-items/{work_item_id}/operations/{operation_id}")
def operation(work_item_id: str, operation_id: str, store: StoreDep, principal: ReadPrincipal) -> dict[str, Any]:
    _work(store, work_item_id, principal)
    with session_scope(store.engine) as session:
        row = session.get(CaseworkCommand, operation_id)
        if row is None or row.work_item_id != work_item_id:
            raise not_found("operation", operation_id)
        return {"operation_id": row.command_id, "state": row.state, "cursor": row.cursor_json, "error": row.error_json}


@router.get("/work-items/{work_item_id}/response-export")
def export_response(work_item_id: str, store: StoreDep, principal: ReadPrincipal) -> dict[str, Any]:
    _work(store, work_item_id, principal)
    with session_scope(store.engine) as session:
        work, flow = session.get(WorkItem, work_item_id), session.get(CaseworkWorkflow, work_item_id)
        response = (
            session.get(ProfessionalResponse, flow.current_response_id) if flow and flow.current_response_id else None
        )
        basis = (
            session.execute(
                select(OutputBasis).where(
                    OutputBasis.work_item_id == work_item_id,
                    OutputBasis.response_id == flow.current_response_id,
                    OutputBasis.valid.is_(True),
                )
            )
            .scalars()
            .first()
            if flow
            else None
        )
        approved = (
            session.execute(
                select(ReviewBasis).where(
                    ReviewBasis.basis_id == basis.basis_id,
                    ReviewBasis.decision == "approved",
                    ReviewBasis.stale_reason.is_(None),
                )
            )
            .scalars()
            .first()
            if basis
            else None
        )
        if response is None or basis is None or approved is None or work.review_status != "approved":
            raise invalid_state("Chỉ response current đã duyệt với basis còn hiệu lực mới được export.")
        return {
            "response_id": response.response_id,
            "version": response.version,
            "sections": response.sections_json,
            "basis_hash": basis.basis_hash,
            "approved_at": approved.decided_at.isoformat() if approved.decided_at else None,
        }


@router.patch("/work-items/{work_item_id}/adr-intake")
def patch_adr(
    work_item_id: str,
    payload: AdrPatchIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    _work(store, work_item_id, principal, write=True)
    with session_scope(store.engine) as session:
        work, flow = session.get(WorkItem, work_item_id), session.get(CaseworkWorkflow, work_item_id)
        if flow.kind != "adr":
            raise invalid_state("Chỉ ADR có adr-intake.")
        if work.version != payload.expected_version:
            raise version_conflict(payload.expected_version, work.version)
        current = dict(flow.adr_intake_json or {})
        current.update(payload.patch)
        facts = current.get("groups") or current.get("minimum_four") or {}
        if isinstance(facts, list):
            facts = {item.get("key"): item for item in facts if isinstance(item, dict)}
        adr = adr_minimum_four(facts)
        current.update(adr)
        current.setdefault("reportability", {"status": "not_assessed"})
        flow.adr_intake_json, flow.input_revision, flow.updated_at = current, flow.input_revision + 1, now()
        work.version, work.etag, work.review_status, work.updated_at = (
            work.version + 1,
            etag_for("work_item", work_item_id, work.version + 1),
            "pending",
            now(),
        )
    return _aggregate(store, work_item_id, principal)


@router.post("/work-items/{work_item_id}/adr-reportability")
def adr_reportability(
    work_item_id: str,
    payload: ReportabilityIn,
    store: StoreDep,
    principal: ReviewPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    work = _work(store, work_item_id, principal)
    if work.version != payload.expected_version:
        raise version_conflict(payload.expected_version, work.version)
    return CaseWorkflowService(store.engine).set_adr_reportability(
        work_item_id=work_item_id,
        status=payload.status,
        assessor=_actor(principal),
        reason=payload.reason,
        policy_reference=payload.policy_reference,
    )


@router.patch("/work-items/{work_item_id}/follow-ups/{follow_up_id}")
def close_follow_up(
    work_item_id: str,
    follow_up_id: str,
    payload: FollowUpPatchIn,
    store: StoreDep,
    principal: RunPrincipal,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    _require_key(idempotency_key)
    work = _work(store, work_item_id, principal, write=True)
    if work.version != payload.expected_version:
        raise version_conflict(payload.expected_version, work.version)
    with session_scope(store.engine) as session:
        row = session.get(FollowUp, follow_up_id)
        if row is None or row.work_item_id != work_item_id:
            raise not_found("follow-up", follow_up_id)
        if row.status not in {"open", "in_progress"}:
            raise invalid_state("Follow-up đã đóng.")
        row.status, row.resolution, row.closed_at = payload.status, payload.resolution, now()
        session.execute(
            update(WorkItem)
            .where(WorkItem.work_item_id == work_item_id, WorkItem.version == payload.expected_version)
            .values(
                version=payload.expected_version + 1,
                etag=etag_for("work_item", work_item_id, payload.expected_version + 1),
                updated_at=now(),
            )
        )
        return {"follow_up_id": row.follow_up_id, "status": row.status, "resolution": row.resolution}
