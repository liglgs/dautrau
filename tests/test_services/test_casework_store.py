"""Kiểm thử lưu trữ lát cắt DI (WorkItem/Response/FollowUp) và bước nâng cấp lược đồ.

Toàn bộ chạy ngoại tuyến trên SQLite trong ``tmp_path``:

* ``test_migration_adds_tables_without_touching_legacy_data`` dựng một cơ sở dữ liệu
  "bản cũ" (14 bảng kho ELT) có dữ liệu, chạy nâng cấp, rồi khẳng định bảng cũ nguyên vẹn;
* các bài còn lại kiểm tra ghi/đọc, khoá lạc quan, lịch sử phiên bản, phiếu trả lời
  theo phiên bản, và việc mở lại cơ sở dữ liệu bằng kết nối mới vẫn thấy dữ liệu.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import insert, text

from scripts.elt.migrate_casework import inspect_state, migrate, rollback
from src.models.schemas import ErrorCode
from src.services.casework.store import CASEWORK_TABLES, CaseWorkStore
from src.services.errors import MvpError
from src.services.warehouse.db import get_warehouse_engine
from src.services.warehouse.models import WarehouseBase

LEGACY_ONLY = [name for name in WarehouseBase.metadata.tables if name not in CASEWORK_TABLES]


def legacy_tables():
    return [WarehouseBase.metadata.tables[name] for name in LEGACY_ONLY]


@pytest.fixture()
def legacy_db(tmp_path: Path):
    """Cơ sở dữ liệu 'bản cũ': chỉ 14 bảng kho ELT, đã có dữ liệu mẫu."""
    engine = get_warehouse_engine(f"sqlite:///{tmp_path / 'warehouse.db'}")
    WarehouseBase.metadata.create_all(engine, tables=legacy_tables())
    with engine.begin() as conn:
        conn.execute(
            insert(WarehouseBase.metadata.tables["drugs"]).values(
                drug_id="drug-ibuprofen",
                name="ibuprofen",
                ingredient="ibuprofen",
                verified=True,
                source="dataset-spec",
                aliases=[],
                metadata_json={},
            )
        )
        conn.execute(
            insert(WarehouseBase.metadata.tables["drug_event_pairs"]).values(
                pair_id="ibuprofen__gastrointestinal-haemorrhage",
                drug_id="drug-ibuprofen",
                drug_name="ibuprofen",
                event_term="Gastrointestinal haemorrhage",
                status="candidate_not_gold",
                source="bundle",
                metadata_json={},
            )
        )
        conn.execute(
            insert(WarehouseBase.metadata.tables["documents"]).values(
                doc_id="doc-1",
                source="pubmed",
                source_id="39466269",
                version=1,
                title="Ibuprofen và xuất huyết tiêu hoá",
                text="Nội dung tài liệu mẫu.",
                text_sha256="a" * 64,
                source_url="https://pubmed.ncbi.nlm.nih.gov/39466269/",
                content_level="abstract_only",
                pair_id="ibuprofen__gastrointestinal-haemorrhage",
                run_id="run-1",
                quality_status="keep",
                quality_flags=[],
                metadata_json={},
            )
        )
    return engine


def count(engine, table: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one())


# --------------------------------------------------------------- nâng cấp lược đồ


def test_migration_adds_tables_without_touching_legacy_data(legacy_db):
    state = inspect_state(legacy_db)
    assert state["missing_casework"] == sorted(CASEWORK_TABLES)
    assert state["missing_legacy"] == []

    report = migrate(legacy_db)

    assert sorted(report["created_tables"]) == sorted(CASEWORK_TABLES)
    assert report["missing_casework"] == []
    assert report["legacy_drift"] == {}
    assert count(legacy_db, "documents") == 1
    assert count(legacy_db, "drugs") == 1
    assert count(legacy_db, "drug_event_pairs") == 1


def test_migration_is_idempotent(legacy_db):
    migrate(legacy_db)
    again = migrate(legacy_db)
    assert again["created_tables"] == []
    assert again["tables_before"] == again["tables_after"]
    assert again["legacy_drift"] == {}


def test_rollback_removes_only_casework_tables(legacy_db):
    migrate(legacy_db)
    dropped = rollback(legacy_db)
    assert sorted(dropped) == sorted(CASEWORK_TABLES)
    state = inspect_state(legacy_db)
    assert state["missing_legacy"] == []
    assert count(legacy_db, "documents") == 1


# ------------------------------------------------------------------ work items


def test_work_item_round_trip_and_restart(tmp_path: Path, legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(
        question="Ibuprofen có gây xuất huyết tiêu hoá không?",
        context={"requester": {"actor_id": "user-1182", "role": "doctor"}},
        scope={"drug": {"value": "ibuprofen", "resolution": "confirmed", "source": "requester"}},
        unknowns=[{"field": "indication", "reason": "chưa có chỉ định"}],
        priority="urgent",
        actor={"actor_id": "user-1182", "role": "doctor"},
    )
    assert created["version"] == 1
    assert created["work_status"] == "draft"
    assert created["run_status"] == "not_started"
    assert created["etag"]

    # "Khởi động lại": engine mới trên cùng tệp vẫn đọc được bản ghi.
    reopened = CaseWorkStore(get_warehouse_engine(f"sqlite:///{tmp_path / 'warehouse.db'}"))
    assert reopened.get_work_item(created["work_item_id"])["question"] == created["question"]
    assert len(reopened.list_work_items()) == 1


def test_update_requires_matching_version_and_keeps_history(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(question="Câu hỏi gốc")
    work_item_id = created["work_item_id"]

    updated = store.update_work_item(
        work_item_id,
        changes={"work_status": "accepted", "priority": "routine"},
        expected_version=1,
        actor={"actor_id": "user-1182", "role": "doctor"},
    )
    assert updated["version"] == 2
    assert updated["work_status"] == "accepted"

    with pytest.raises(MvpError) as conflict:
        store.update_work_item(
            work_item_id, changes={"work_status": "completed"}, expected_version=1, actor=None
        )
    assert conflict.value.code == ErrorCode.VERSION_CONFLICT
    assert conflict.value.status == 409
    # Không ghi gì khi xung đột.
    assert store.get_work_item(work_item_id)["version"] == 2

    history = store.history(entity="work_item", entity_id=work_item_id)
    assert [item["entity_version"] for item in history] == [1, 2]
    assert [item["revision"] for item in history] == [1, 2]
    assert history[0]["snapshot"]["work_status"] == "draft"
    assert history[0]["snapshot"]["question"] == "Câu hỏi gốc"
    assert history[1]["change_kind"] == "updated"
    assert history[1]["changed_fields"] == ["priority", "work_status"]


def test_update_rejects_unknown_fields_and_missing_version(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(question="Câu hỏi gốc")
    work_item_id = created["work_item_id"]

    with pytest.raises(MvpError) as unknown:
        store.update_work_item(work_item_id, changes={"gold_label": "positive"}, expected_version=1, actor=None)
    assert unknown.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as missing:
        store.update_work_item(work_item_id, changes={"work_status": "accepted"}, expected_version=None, actor=None)
    assert missing.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as bad_value:
        store.update_work_item(work_item_id, changes={"work_status": "done"}, expected_version=1, actor=None)
    assert bad_value.value.code == ErrorCode.INVALID_REQUEST
    assert store.get_work_item(work_item_id)["version"] == 1


def test_two_sequential_updates_keep_both_versions(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(question="Hai người cùng sửa")
    work_item_id = created["work_item_id"]

    store.update_work_item(
        work_item_id, changes={"work_status": "accepted"}, expected_version=1, actor={"actor_id": "user-1182"}
    )
    store.update_work_item(
        work_item_id, changes={"work_status": "in_progress"}, expected_version=2, actor={"actor_id": "user-2044"}
    )

    history = store.history(entity="work_item", entity_id=work_item_id)
    assert [(item["entity_version"], item["snapshot"]["work_status"]) for item in history] == [
        (1, "draft"),
        (2, "accepted"),
        (3, "in_progress"),
    ]
    assert history[1]["updated_by"]["actor_id"] == "user-1182"


# -------------------------------------------------- liên kết điều tra và bằng chứng


def test_investigation_link_and_evidence_bundle(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]

    link = store.add_investigation_link(
        work_item_id, investigation_id="INV-abc", purpose="initial", state="queued", actor={"actor_id": "user-1182"}
    )
    assert link["state"] == "queued"
    store.update_investigation_link(link["link_id"], state="completed", run_summary={"documents": 12})
    assert store.list_investigation_links(work_item_id)[0]["state"] == "completed"

    bundle = store.add_evidence_bundle(
        work_item_id,
        investigation_id="INV-abc",
        items=[{"doc_id": "doc-1", "source": "pubmed", "stance": "supports", "quote": "câu trích dẫn"}],
        gaps=[{"kind": "no_vietnamese_source", "detail": "chưa có dữ liệu Việt Nam"}],
        coverage={
            "documents_retrieved": 12,
            "sources_ok": ["pubmed"],
            "sources_empty": [],
            "sources_error": ["faers"],
            "abstract_only": True,
        },
        assessment_status="insufficient_evidence",
        limitations=["Chỉ có phần tóm tắt."],
    )
    assert bundle["items"][0]["doc_id"] == "doc-1"
    assert bundle["coverage"]["documents_retrieved"] == 12
    assert store.get_evidence_bundle(bundle["bundle_id"])["gaps"][0]["kind"] == "no_vietnamese_source"

    with pytest.raises(MvpError) as bad:
        store.add_evidence_bundle(
            work_item_id,
            investigation_id="INV-abc",
            items=[],
            gaps=[],
            coverage={},
            assessment_status="chac_chan_dung",
        )
    assert bad.value.code == ErrorCode.INVALID_REQUEST


def test_unknown_work_item_is_not_found(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    with pytest.raises(MvpError) as missing:
        store.get_work_item("wi_khong_ton_tai")
    assert missing.value.code == ErrorCode.NOT_FOUND
    with pytest.raises(MvpError) as missing_link:
        store.add_investigation_link("wi_khong_ton_tai", investigation_id="INV-x")
    assert missing_link.value.code == ErrorCode.NOT_FOUND


# ------------------------------------------------------------- phiếu trả lời


def test_save_response_keeps_superseded_version(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]

    first = store.save_response(
        work_item_id,
        sections=[{"key": "summary", "text": "Bản nháp đầu."}],
        drafted_by={"actor_id": "user-2044", "role": "pharmacist"},
    )
    assert first["version"] == 1
    assert first["status"] == "draft"
    assert first["supersedes"] is None

    second = store.save_response(
        work_item_id,
        sections=[{"key": "summary", "text": "Bản nháp sau khi bổ sung bằng chứng."}],
        status="in_review",
        assessment_status="supported_for_scope",
    )
    assert second["version"] == 2
    assert second["supersedes"] == first["response_id"]

    all_versions = store.list_responses(work_item_id)
    assert [item["version"] for item in all_versions] == [1, 2]
    assert all_versions[0]["status"] == "superseded"
    assert all_versions[0]["sections"][0]["text"] == "Bản nháp đầu."
    assert [item["response_id"] for item in store.list_responses(work_item_id, include_superseded=False)] == [
        second["response_id"]
    ]

    history = store.history(entity="response", entity_id=first["response_id"])
    assert history[-1]["change_kind"] == "superseded"
    assert history[-1]["snapshot"]["status"] == "superseded"


def test_review_updates_status_and_is_appended(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    response = store.save_response(work_item_id, sections=[{"key": "summary", "text": "Nội dung"}])

    review = store.add_review(
        entity="response",
        entity_id=response["response_id"],
        action="approve",
        reviewer={"actor_id": "user-3301", "role": "reviewer"},
        reason="Bằng chứng khớp phạm vi.",
    )
    assert review["previous_status"] == "draft"
    assert review["new_status"] == "approved"
    assert store.get_response(response["response_id"])["status"] == "approved"

    reviews = store.list_reviews(entity="response", entity_id=response["response_id"])
    assert len(reviews) == 1
    assert reviews[0]["reviewer"]["actor_id"] == "user-3301"

    with pytest.raises(MvpError) as bad_entity:
        store.add_review(entity="dossier", entity_id="x", action="approve", reviewer={"actor_id": "user-3301"})
    assert bad_entity.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as bad_reviewer:
        store.add_review(entity="response", entity_id=response["response_id"], action="approve", reviewer={})
    assert bad_reviewer.value.code == ErrorCode.INVALID_REQUEST


def test_review_of_work_item_bumps_version_and_keeps_history(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]

    store.add_review(
        entity="work_item",
        entity_id=work_item_id,
        action="request_changes",
        reviewer={"actor_id": "user-3301", "role": "reviewer"},
        reason="Thiếu phạm vi chỉ định.",
    )
    updated = store.get_work_item(work_item_id)
    assert updated["review_status"] == "changes_requested"
    assert updated["version"] == 2
    history = store.history(entity="work_item", entity_id=work_item_id)
    assert history[-1]["change_kind"] == "reviewed"
    assert history[-1]["snapshot"]["review_status"] == "changes_requested"


# ------------------------------------------------------------------ theo dõi


def test_follow_up_lifecycle(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]

    follow_up = store.add_follow_up(
        work_item_id,
        kind="recheck_source",
        note="Kiểm lại DailyMed sau khi nhãn cập nhật.",
        assignee={"actor_id": "user-2044", "role": "pharmacist"},
    )
    assert follow_up["status"] == "open"

    closed = store.update_follow_up(
        follow_up["follow_up_id"], status="done", resolution="Đã kiểm lại, nhãn không đổi."
    )
    assert closed["status"] == "done"
    assert closed["closed_at"] is not None
    assert store.list_follow_ups(work_item_id)[0]["resolution"].startswith("Đã kiểm lại")

    with pytest.raises(MvpError) as bad_kind:
        store.add_follow_up(work_item_id, kind="khong_hop_le", note="ghi chú")
    assert bad_kind.value.code == ErrorCode.INVALID_REQUEST


def test_bundle_view_and_counts(legacy_db):
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    store.add_follow_up(work_item_id, kind="close", note="Đóng ca.")

    bundle = store.work_item_bundle(work_item_id)
    assert set(bundle) == {"work_item", "investigation_links", "evidence_bundles", "responses", "follow_ups"}
    assert bundle["follow_ups"][0]["kind"] == "close"

    counts = store.counts()
    assert set(counts) == set(CASEWORK_TABLES)
    assert counts["work_items"] == 1
    assert counts["follow_ups"] == 1
    assert counts["version_refs"] >= 2
