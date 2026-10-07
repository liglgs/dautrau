"""Focused durable workflow tests; no route or runner dependency."""

from __future__ import annotations

import pytest

from src.models.schemas import ErrorCode
from src.services.casework.models import InputRevision
from src.services.casework.store import CaseWorkStore
from src.services.errors import MvpError
from src.services.warehouse.db import get_warehouse_engine, session_scope


@pytest.fixture()
def store(tmp_path):
    return CaseWorkStore(get_warehouse_engine(f"sqlite:///{tmp_path / 'workflow.db'}"))


def _actor(identifier="pharmacist-1"):
    return {"id": identifier, "role": "pharmacist"}


def _source(store, work_item_id):
    with session_scope(store.engine) as session:
        revision = session.query(InputRevision).filter_by(work_item_id=work_item_id, revision=1).one()
        return revision.sources_json[0]


def test_raw_intake_is_durable_and_retry_is_idempotent(store):
    kwargs = dict(kind="di", raw_text="Có cần giảm liều ở người cao tuổi?", actor=_actor(), idempotency_key="tap-once")
    first = store.create_intake(**kwargs)
    replay = store.create_intake(**kwargs)

    assert replay == first
    assert store.counts()["work_items"] == 1
    reopened = CaseWorkStore(store.engine)
    assert reopened.get_work_item(first["work_item_id"])["question"] == kwargs["raw_text"]

    with pytest.raises(MvpError) as conflict:
        store.create_intake(**{**kwargs, "raw_text": "Payload khác"})
    assert conflict.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_unicode_code_point_spans_and_unknown_semantics(store):
    intake = store.create_intake(kind="di", raw_text="💊 Metformin gây buồn nôn", actor=_actor())
    source = _source(store, intake["work_item_id"])
    text = source["text"]
    start = text.index("Metformin")
    result = store.update_fields(
        work_item_id=intake["work_item_id"],
        expected_version=1,
        actor=_actor(),
        assertions=[
            {
                "field_key": "drug",
                "value": "metformin",
                "status": "proposed",
                "source_spans": [
                    {
                        "source_id": source["source_id"],
                        "start": start,
                        "end": start + len("Metformin"),
                        "quote": "Metformin",
                    }
                ],
            },
            {
                "field_key": "route",
                "value": None,
                "status": "unknown",
                "unknown_reason": "Không được ghi nhận",
                "source_spans": [],
            },
        ],
    )
    assert result["field_assertions"][0]["source_spans"][0]["start"] == 2  # emoji is one Unicode code point
    assert result["field_assertions"][1]["status"] == "unknown"

    with pytest.raises(MvpError):
        store.update_fields(
            work_item_id=intake["work_item_id"],
            expected_version=2,
            actor=_actor(),
            assertions=[
                {
                    "field_key": "drug",
                    "value": "metformin",
                    "status": "proposed",
                    "source_spans": [
                        {"source_id": source["source_id"], "start": start, "end": start + 3, "quote": "wrong"}
                    ],
                }
            ],
        )


def test_open_clarification_is_semantically_deduplicated_and_unknown_closes_it(store):
    intake = store.create_intake(kind="di", raw_text="Câu hỏi chưa đủ dữ kiện", actor=_actor())
    first = store.create_clarification(
        work_item_id=intake["work_item_id"],
        field_key="dose",
        question="Liều bao nhiêu?",
        classification="useful_for_completeness",
        semantic_key="dose",
        actor=_actor(),
    )
    assert (
        store.create_clarification(
            work_item_id=intake["work_item_id"],
            field_key="dose",
            question="Liều bao nhiêu?",
            classification="useful_for_completeness",
            semantic_key="dose",
            actor=_actor(),
        )["clarification_id"]
        == first["clarification_id"]
    )
    answered = store.answer_clarification(
        work_item_id=intake["work_item_id"],
        clarification_id=first["clarification_id"],
        expected_version=1,
        actor=_actor(),
        answer=None,
        unknown=True,
    )
    assert answered["status"] == "unknown"


def test_field_mutation_uses_work_item_cas(store):
    intake = store.create_intake(kind="di", raw_text="Câu hỏi", actor=_actor())
    source = _source(store, intake["work_item_id"])
    store.update_fields(
        work_item_id=intake["work_item_id"],
        expected_version=1,
        actor=_actor(),
        assertions=[
            {
                "field_key": "purpose",
                "value": "dose",
                "status": "proposed",
                "source_spans": [{"source_id": source["source_id"], "start": 0, "end": 3, "quote": "Câu"}],
            }
        ],
    )
    with pytest.raises(MvpError) as conflict:
        store.update_fields(work_item_id=intake["work_item_id"], expected_version=1, actor=_actor(), assertions=[])
    assert conflict.value.code == ErrorCode.VERSION_CONFLICT


@pytest.mark.parametrize("present", range(5))
def test_adr_persists_with_zero_to_four_minimum_groups(store, present):
    facts = {
        name: {"status": "present" if index < present else "missing", "assertion_refs": [], "confirmed_by": None}
        for index, name in enumerate(
            (
                "identifiable_patient",
                "identifiable_reporter",
                "suspected_medicinal_product",
                "suspected_adverse_reaction",
            )
        )
    }
    intake = store.create_intake(
        kind="adr", raw_text="Có biểu hiện bất lợi sau dùng thuốc", actor=_actor(), adr_facts=facts
    )
    assert intake["adr"]["validity"] == ("complete" if present == 4 else "incomplete")
    assert intake["adr"]["reportability"]["status"] == "not_assessed"


def test_material_change_invalidates_basis_and_author_cannot_self_review(store):
    intake = store.create_intake(kind="di", raw_text="Ibuprofen có gây xuất huyết?", actor=_actor("author"))
    basis = store.create_output_basis(
        work_item_id=intake["work_item_id"],
        response_id="response-1",
        response_version=1,
        basis={"input_revision": 1, "response_content_hash": "a" * 64},
        author_ids=["author"],
    )
    with pytest.raises(MvpError) as self_review:
        store.decide_workflow_review(
            work_item_id=intake["work_item_id"],
            basis_hash=basis["basis_hash"],
            reviewer=_actor("author"),
            decision="approved",
            expected_version=1,
        )
    assert self_review.value.code == ErrorCode.INVALID_STATE

    source = _source(store, intake["work_item_id"])
    store.update_fields(
        work_item_id=intake["work_item_id"],
        expected_version=1,
        actor=_actor("author"),
        assertions=[
            {
                "field_key": "drug",
                "value": "ibuprofen",
                "status": "confirmed",
                "source_spans": [{"source_id": source["source_id"], "start": 0, "end": 9, "quote": "Ibuprofen"}],
            }
        ],
    )
    with pytest.raises(MvpError):
        store.decide_workflow_review(
            work_item_id=intake["work_item_id"],
            basis_hash=basis["basis_hash"],
            reviewer=_actor("reviewer"),
            decision="approved",
            expected_version=2,
        )
