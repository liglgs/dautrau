"""Kiểm thử lưu trữ lát cắt DI (WorkItem/Response/FollowUp) và bước nâng cấp lược đồ.

Toàn bộ chạy ngoại tuyến trên SQLite trong ``tmp_path``:

* ``test_migration_adds_tables_without_touching_legacy_data`` dựng một cơ sở dữ liệu
  "bản cũ" (14 bảng kho ELT) có dữ liệu, chạy nâng cấp, rồi khẳng định bảng cũ nguyên vẹn;
* các bài còn lại kiểm tra ghi/đọc, khoá lạc quan, lịch sử phiên bản, phiếu trả lời
  theo phiên bản, và việc mở lại cơ sở dữ liệu bằng kết nối mới vẫn thấy dữ liệu.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import cache
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
    assert [item["version"] for item in history] == [1, 2]
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
    assert [(item["version"], item["snapshot"]["work_status"]) for item in history] == [
        (1, "draft"),
        (2, "accepted"),
        (3, "in_progress"),
    ]
    assert history[1]["updated_by"] == {"id": "user-1182"}


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
        items=[
            {
                "evidence_id": "EVI-store-1",
                "doc_id": "doc-1",
                "source": "pubmed",
                "stance": "supports",
                "quote": "câu trích dẫn",
                "locator": {"start": 0, "end": 14, "section": "Tóm tắt"},
                "retrieval": "abstract_only",
            }
        ],
        gaps=[{"kind": "missing_source", "detail": "chưa có dữ liệu Việt Nam"}],
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
    assert store.get_evidence_bundle(bundle["bundle_id"])["gaps"][0]["kind"] == "missing_source"

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
        expected_version=1,
    )
    assert review["previous_status"] == "draft"
    assert review["new_status"] == "approved"
    assert store.get_response(response["response_id"])["status"] == "approved"

    reviews = store.list_reviews(entity="response", entity_id=response["response_id"])
    assert len(reviews) == 1
    assert reviews[0]["reviewer"] == {"id": "user-3301", "role": "reviewer"}

    with pytest.raises(MvpError) as bad_entity:
        store.add_review(entity="dossier", entity_id="x", action="approve", reviewer={"actor_id": "user-3301"})
    assert bad_entity.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as bad_reviewer:
        store.add_review(
            entity="response",
            entity_id=response["response_id"],
            action="approve",
            reviewer={},
            expected_version=2,
        )
    assert bad_reviewer.value.code == ErrorCode.INVALID_REQUEST

    # Thiếu expected_version thì không duyệt được: đọc rồi ghi phải có mốc phiên bản.
    with pytest.raises(MvpError) as missing_version:
        store.add_review(
            entity="response",
            entity_id=response["response_id"],
            action="approve",
            reviewer={"id": "user-3301", "role": "reviewer"},
        )
    assert missing_version.value.code == ErrorCode.INVALID_REQUEST


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


# ------------------------------------------- khoá lạc quan khi hai người ghi song song


def _run_two_writers(store, work_item_id, *, expected_version: int):
    """Cho hai luồng cùng sửa một yêu cầu với cùng ``expected_version``.

    Trả về ``(thành công, lỗi)`` — mỗi bên là một phần tử, ``None`` nghĩa là không có.
    """
    import threading

    barrier = threading.Barrier(2, timeout=30)
    results: dict[str, object] = {}

    def writer(name: str, work_status: str) -> None:
        try:
            barrier.wait()
            results[name] = store.update_work_item(
                work_item_id,
                changes={"work_status": work_status},
                expected_version=expected_version,
                actor={"id": name, "role": "doctor"},
            )
        except BaseException as exc:  # noqa: BLE001 - giữ nguyên để khẳng định bên dưới
            results[name] = exc

    threads = [
        threading.Thread(target=writer, args=("user-1182", "accepted")),
        threading.Thread(target=writer, args=("user-2044", "in_progress")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    successes = [value for value in results.values() if isinstance(value, dict)]
    failures = [value for value in results.values() if isinstance(value, BaseException)]
    return successes, failures


def test_concurrent_updates_have_exactly_one_winner(legacy_db):
    """Đua nhau cùng ``expected_version``: đúng một người thắng, người kia nhận 409.

    Đây là bài kiểm tra chống mất dữ liệu (lost update): bản cũ đọc rồi mới ghi nên cả
    hai đều thắng và bản ghi sau đè bản ghi trước.
    """
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Hai người cùng sửa")["work_item_id"]

    successes, failures = _run_two_writers(store, work_item_id, expected_version=1)

    assert len(successes) == 1, successes
    assert len(failures) == 1, failures
    assert isinstance(failures[0], MvpError)
    assert failures[0].code == ErrorCode.VERSION_CONFLICT
    assert failures[0].status == 409

    current = store.get_work_item(work_item_id)
    assert current["version"] == 2
    assert current["work_status"] == successes[0]["work_status"]

    history = store.history(entity="work_item", entity_id=work_item_id)
    assert [(item["revision"], item["version"]) for item in history] == [(1, 1), (2, 2)]


def test_concurrent_saves_leave_exactly_one_current_response(legacy_db):
    """Hai lần lưu phiếu song song không được tạo hai bản 'hiện hành' cùng lúc."""
    import threading

    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]

    barrier = threading.Barrier(2, timeout=30)
    results: dict[str, object] = {}

    def saver(name: str, text: str) -> None:
        try:
            barrier.wait()
            results[name] = store.save_response(work_item_id, sections=[{"key": "summary", "text": text}])
        except BaseException as exc:  # noqa: BLE001
            results[name] = exc

    threads = [
        threading.Thread(target=saver, args=("a", "Bản A")),
        threading.Thread(target=saver, args=("b", "Bản B")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    # Bên thua (nếu có) phải nhận 409 sạch sẽ, không phải lỗi hệ thống.
    for value in results.values():
        assert isinstance(value, dict) or (isinstance(value, MvpError) and value.status == 409), value

    # Bất biến quan trọng: không bao giờ có hai bản "hiện hành" cùng lúc.
    current = store.list_responses(work_item_id, include_superseded=False)
    assert len(current) == 1
    versions = [item["version"] for item in store.list_responses(work_item_id)]
    assert versions == sorted(set(versions)), versions
    assert current[0]["version"] == max(versions)


# ------------------------------------------------- kiểm tra kiểu và trạng thái


def test_actor_is_normalised_to_contract_shape(legacy_db):
    """Đầu vào kiểu ``actor_id`` được chuẩn hoá về ``Actor`` của hợp đồng."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(question="Câu hỏi", actor={"actor_id": "user-1182", "role": "doctor"})
    assert created["owner"] is None

    history = store.history(entity="work_item", entity_id=created["work_item_id"])
    assert history[0]["updated_by"] == {"id": "user-1182", "role": "doctor"}

    with pytest.raises(MvpError) as bad_role:
        store.create_work_item(question="Câu hỏi", actor={"id": "user-1182", "role": "bác sĩ"})
    assert bad_role.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as blank_id:
        store.create_work_item(question="Câu hỏi", owner={"id": "   "})
    assert blank_id.value.code == ErrorCode.INVALID_REQUEST


def test_validation_rejects_contract_invalid_payloads(legacy_db):
    """Không nhận dữ liệu sai kiểu hay rỗng mà hợp đồng đã cấm."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]

    with pytest.raises(MvpError) as bad_scope:
        store.create_work_item(question="Câu hỏi", scope=["không phải đối tượng"])
    assert bad_scope.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as bad_unknowns:
        store.create_work_item(question="Câu hỏi", unknowns={"không": "phải danh sách"})
    assert bad_unknowns.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as blank_question:
        store.create_work_item(question="   ")
    assert blank_question.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as bad_version:
        store.update_work_item(work_item_id, changes={"work_status": "accepted"}, expected_version="hai")
    assert bad_version.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as empty_sections:
        store.save_response(work_item_id, sections=[])
    assert empty_sections.value.code == ErrorCode.INVALID_REQUEST

    with pytest.raises(MvpError) as bad_limit:
        store.list_work_items(limit="nhiều")
    assert bad_limit.value.code == ErrorCode.INVALID_REQUEST

    assert store.get_work_item(work_item_id)["version"] == 1


def test_duplicate_identifier_is_reported_as_conflict(legacy_db):
    """Mã do người gọi đặt mà trùng thì trả 409, không phải lỗi hệ thống."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    store.create_work_item(question="Câu hỏi", work_item_id="wi_co_dinh")

    with pytest.raises(MvpError) as duplicate:
        store.create_work_item(question="Câu hỏi khác", work_item_id="wi_co_dinh")
    assert duplicate.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert duplicate.value.status == 409


def test_review_of_superseded_response_is_rejected(legacy_db):
    """Phiếu đã bị thay thế thì không duyệt được, và mỗi lần duyệt tăng phiên bản."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    first = store.save_response(work_item_id, sections=[{"key": "summary", "text": "Bản đầu."}])
    store.save_response(work_item_id, sections=[{"key": "summary", "text": "Bản sau."}])

    with pytest.raises(MvpError) as superseded:
        store.add_review(
            entity="response",
            entity_id=first["response_id"],
            action="approve",
            reviewer={"id": "user-3301", "role": "reviewer"},
        )
    assert superseded.value.code == ErrorCode.INVALID_STATE

    current = store.list_responses(work_item_id, include_superseded=False)
    assert len(current) == 1
    second_id = current[0]["response_id"]

    review = store.add_review(
        entity="response",
        entity_id=second_id,
        action="approve",
        reviewer={"id": "user-3301", "role": "reviewer"},
        expected_version=2,
    )
    assert review["new_status"] == "approved"
    approved = store.get_response(second_id)
    assert approved["status"] == "approved"
    assert approved["version"] == 3
    assert approved["etag"] != current[0]["etag"]

    with pytest.raises(MvpError) as stale:
        store.add_review(
            entity="response",
            entity_id=second_id,
            action="approve",
            reviewer={"id": "user-3301", "role": "reviewer"},
            expected_version=2,
        )
    assert stale.value.code == ErrorCode.VERSION_CONFLICT


def test_work_item_document_lists_related_ids(legacy_db):
    """Bản chiếu yêu cầu mang mã của liên kết, phiếu trả lời và việc theo dõi."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    link = store.add_investigation_link(work_item_id, investigation_id="INV-abc")
    response = store.save_response(work_item_id, sections=[{"key": "summary", "text": "Nội dung."}])
    follow_up = store.add_follow_up(work_item_id, kind="monitor_case", note="Theo dõi thêm.")

    document = store.get_work_item(work_item_id)
    assert document["investigation_ids"] == [link["link_id"]]
    assert document["response_ids"] == [response["response_id"]]
    assert document["follow_up_ids"] == [follow_up["follow_up_id"]]
    assert "created_by" not in document


def test_history_rows_keep_contract_version_reference(legacy_db):
    """Mỗi dòng lịch sử vừa khớp ``VersionRef`` vừa giữ phần nhật ký của kho."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(question="Câu hỏi")
    work_item_id = created["work_item_id"]
    updated = store.update_work_item(
        work_item_id, changes={"work_status": "accepted"}, expected_version=1, actor={"id": "user-1182"}
    )

    rows = store.history(entity="work_item", entity_id=work_item_id)
    assert len(rows) == 2
    for row in rows:
        assert set(row) >= {"entity", "id", "version", "etag", "updated_at", "updated_by", "revision", "change_kind"}
        assert row["id"] == work_item_id
        assert row["entity"] == "work_item"
        assert len(row["etag"]) == 32
        assert row["updated_at"].endswith("+00:00")
    assert rows[-1]["version"] == updated["version"]
    assert rows[-1]["etag"] == updated["etag"]
    assert rows[-1]["snapshot"]["work_status"] == "accepted"


# ------------------------------------------- hợp đồng: bản chiếu của kho phải khớp lược đồ

# Sáu trường lõi mà bản chiếu lịch sử chia sẻ với ``VersionRef``; phần còn lại là mở rộng.
_VERSION_REF_KEYS = ("entity", "id", "version", "etag", "updated_at", "updated_by")


@cache
def _contract_validator(def_name: str):
    """Bộ kiểm tra lược đồ hospital-v2 cho một định nghĩa, đọc tệp hợp đồng đúng một lần."""
    import json

    from jsonschema import Draft202012Validator

    root = Path(__file__).resolve().parents[2]
    schemas = json.loads((root / "docs/spec/hospital-v2/schemas.json").read_text(encoding="utf-8"))
    return Draft202012Validator({"$ref": f"#/$defs/{def_name}", "$defs": schemas["$defs"]})


def _assert_matches_contract(def_name: str, instance: dict) -> None:
    errors = sorted(_contract_validator(def_name).iter_errors(instance), key=lambda item: list(item.path))
    assert not errors, f"{def_name}: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_store_documents_match_the_hospital_contract(legacy_db):
    """Mọi bản chiếu của kho phải vượt qua lược đồ hospital-v2.

    Đây là lưới chống lệch hợp đồng: đổi tên trường (``actor_id`` → ``id``), thêm trường
    bị cấm (``created_by`` trong WorkItem) hay bỏ trường bắt buộc (``investigation_ids``)
    đều làm bài này đỏ.
    """
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    doctor = {"actor_id": "user-1182", "role": "doctor", "unit": "Khoa Dược"}
    work_item = store.create_work_item(
        question="Ibuprofen có gây xuất huyết tiêu hoá không?",
        context={
            "request_id": "req-1",
            "requester": {"id": "user-1182", "role": "doctor"},
            "channel": "web",
            "received_at": "2026-10-05T08:00:00Z",
            "raw_text": "Nhờ tra cứu giúp.",
            "language": "vi",
        },
        scope={
            "drug": {"value": "ibuprofen", "resolution": "confirmed"},
            "event": {"value": "xuất huyết tiêu hoá", "resolution": "candidate"},
        },
        unknowns=[{"field": "event", "reason": "chưa rõ biến cố", "needs_confirmation": True}],
        owner=doctor,
        actor=doctor,
    )
    _assert_matches_contract("WorkItem", work_item)
    work_item_id = work_item["work_item_id"]

    link = store.add_investigation_link(work_item_id, investigation_id="INV-abc", purpose="initial", state="running")
    _assert_matches_contract("InvestigationLink", link)

    bundle = store.add_evidence_bundle(
        work_item_id,
        investigation_id="INV-abc",
        claim={"claim_text": "Ibuprofen gây xuất huyết tiêu hoá."},
        items=[
            {
                "evidence_id": "ev-1",
                "doc_id": "doc-1",
                "source": "pubmed",
                "stance": "supports",
                "quote": "Nguy cơ xuất huyết tiêu hoá tăng theo liều.",
                "locator": {"start": 0, "end": 43, "section": "abstract"},
                "retrieval": "abstract_only",
            }
        ],
        gaps=[{"kind": "not_readable", "detail": "Chỉ có tóm tắt, không có toàn văn."}],
        coverage={
            "documents_retrieved": 1,
            "sources_ok": ["pubmed"],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": True,
        },
        assessment_status="insufficient_evidence",
        source_errors=[],
        limitations=["Chỉ có tóm tắt PubMed."],
    )
    _assert_matches_contract("EvidenceBundle", bundle)

    response = store.save_response(
        work_item_id,
        sections=[{"key": "summary", "title": "Tóm tắt", "text": "Cần thêm bằng chứng.", "citations": []}],
        drafted_by={"actor_id": "user-2044", "role": "pharmacist"},
        coverage={
            "documents_retrieved": 1,
            "sources_ok": ["pubmed"],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": True,
        },
    )
    _assert_matches_contract("ProfessionalResponse", response)

    review = store.add_review(
        entity="response",
        entity_id=response["response_id"],
        action="request_changes",
        reviewer={"actor_id": "user-3301", "role": "reviewer"},
        reason="Bổ sung bằng chứng toàn văn.",
        expected_version=1,
    )
    _assert_matches_contract("ReviewRef", review)

    follow_up = store.add_follow_up(
        work_item_id,
        kind="request_information",
        note="Hỏi lại khoa lâm sàng về thời điểm khởi phát.",
        assignee={"actor_id": "user-2044", "role": "pharmacist"},
    )
    _assert_matches_contract("FollowUp", follow_up)

    for row in store.history(entity="work_item", entity_id=work_item_id):
        # Dòng lịch sử là bản mở rộng của VersionRef; phần lõi phải khớp lược đồ.
        _assert_matches_contract("VersionRef", {key: row[key] for key in _VERSION_REF_KEYS})

    bundle_view = store.work_item_bundle(work_item_id)
    _assert_matches_contract("WorkItem", bundle_view["work_item"])
    assert bundle_view["work_item"]["investigation_ids"] == [link["link_id"]]
    assert bundle_view["work_item"]["response_ids"] == [response["response_id"]]
    assert bundle_view["work_item"]["follow_up_ids"] == [follow_up["follow_up_id"]]


def test_concurrent_reviews_of_one_response_keep_one_decision(legacy_db):
    """Hai người duyệt cùng một phiếu: đúng một quyết định thắng, quyết định kia bị từ chối.

    Trước đây nhánh duyệt phiếu là đọc-rồi-ghi nên cả hai đều báo thành công, một quyết
    định biến mất, và nhật ký có hai dòng cùng một số phiên bản.
    """
    import threading

    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    response = store.save_response(work_item_id, sections=[{"key": "summary", "text": "Nội dung."}])

    barrier = threading.Barrier(2, timeout=30)
    results: dict[str, object] = {}

    def reviewer(name: str, action: str) -> None:
        try:
            barrier.wait()
            results[name] = store.add_review(
                entity="response",
                entity_id=response["response_id"],
                action=action,
                reviewer={"id": name, "role": "reviewer"},
                expected_version=1,
            )
        except BaseException as exc:  # noqa: BLE001
            results[name] = exc

    threads = [
        threading.Thread(target=reviewer, args=("user-3301", "approve")),
        threading.Thread(target=reviewer, args=("user-3302", "reject")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    winners = [value for value in results.values() if isinstance(value, dict)]
    losers = [value for value in results.values() if isinstance(value, BaseException)]
    assert len(winners) == 1, results
    assert len(losers) == 1, results
    assert isinstance(losers[0], MvpError) and losers[0].status == 409, losers[0]

    final = store.get_response(response["response_id"])
    assert final["version"] == 2
    assert final["status"] == winners[0]["new_status"]

    # Nhật ký không được có hai dòng cùng một số phiên bản cho cùng thực thể.
    rows = store.history(entity="response", entity_id=response["response_id"])
    versions = [row["version"] for row in rows]
    assert versions == sorted(set(versions)), versions
    assert len(store.list_reviews(entity="response", entity_id=response["response_id"])) == 1


def test_review_of_work_item_logs_one_row_per_version(legacy_db):
    """Duyệt yêu cầu chỉ ghi *một* dòng nhật ký cho phiên bản mới, không phải hai."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]

    store.add_review(
        entity="work_item",
        entity_id=work_item_id,
        action="request_changes",
        reviewer={"id": "user-3301", "role": "reviewer"},
    )
    rows = store.history(entity="work_item", entity_id=work_item_id)
    assert [(row["revision"], row["version"]) for row in rows] == [(1, 1), (2, 2)]
    assert [row["change_kind"] for row in rows] == ["created", "reviewed"]


def test_second_current_response_is_rejected_by_the_database(legacy_db):
    """Ràng buộc "một bản hiện hành" là bảo đảm của cơ sở dữ liệu, không chỉ của mã."""
    from sqlalchemy import insert as sql_insert
    from sqlalchemy.exc import IntegrityError

    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    store.save_response(work_item_id, sections=[{"key": "summary", "text": "Bản đầu."}])

    with pytest.raises(IntegrityError):
        with legacy_db.begin() as conn:
            conn.execute(
                sql_insert(WarehouseBase.metadata.tables["professional_responses"]).values(
                    response_id="resp_chen_ngang",
                    work_item_id=work_item_id,
                    version=9,
                    etag="x",
                    status="draft",
                    sections_json=[],
                    assessment_status="insufficient_evidence",
                    coverage_json={},
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )


def test_validation_rejects_non_string_optional_fields(legacy_db):
    """``revision_of``/``revision_reason``/``reason`` phải là chuỗi, không được làm nổ 500."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)

    with pytest.raises(MvpError) as bad_reason:
        store.create_work_item(question="Câu hỏi", revision_reason=123)
    assert bad_reason.value.code == ErrorCode.INVALID_REQUEST

    created = store.create_work_item(question="Câu hỏi")
    with pytest.raises(MvpError) as bad_patch:
        store.update_work_item(
            created["work_item_id"], changes={"revision_reason": {"a": 1}}, expected_version=1
        )
    assert bad_patch.value.code == ErrorCode.INVALID_REQUEST

    response = store.save_response(created["work_item_id"], sections=[{"key": "summary", "text": "Nội dung."}])
    with pytest.raises(MvpError) as bad_review_reason:
        store.add_review(
            entity="response",
            entity_id=response["response_id"],
            action="approve",
            reviewer={"id": "user-3301", "role": "reviewer"},
            reason=123,
            expected_version=1,
        )
    assert bad_review_reason.value.code == ErrorCode.INVALID_REQUEST


def test_identifier_arguments_are_validated(legacy_db):
    """Mã truyền vào phải là chuỗi; nếu không thì 422, không phải lỗi hệ thống."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)

    for call in (
        lambda: store.get_work_item({"a": 1}),
        lambda: store.list_responses(None),
        lambda: store.list_investigation_links(["x"]),
        lambda: store.get_evidence_bundle(7),
        lambda: store.work_item_bundle({"a": 1}),
    ):
        with pytest.raises(MvpError) as bad_id:
            call()
        assert bad_id.value.code == ErrorCode.INVALID_REQUEST


def test_store_can_skip_schema_creation(legacy_db):
    """``ensure_schema=False`` cho đường chỉ đọc và cho nhiều tiến trình khởi động cùng lúc."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db, ensure_schema=False)
    created = store.create_work_item(question="Câu hỏi")
    assert store.get_work_item(created["work_item_id"])["question"] == "Câu hỏi"


def test_migration_refuses_to_index_duplicate_keys(legacy_db):
    """Có khoá trùng thì dừng trước khi tạo chỉ mục duy nhất, không để lược đồ nửa vời."""
    from sqlalchemy import insert as sql_insert
    from sqlalchemy import text as sql_text

    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    store.save_response(work_item_id, sections=[{"key": "summary", "text": "Bản đầu."}])

    # Bỏ ràng buộc rồi cố tình chèn hai bản cùng số phiên bản, đúng kiểu dữ liệu bản cũ để lại.
    with legacy_db.begin() as conn:
        conn.execute(sql_text('DROP INDEX IF EXISTS "uq_response_version"'))
        conn.execute(
            sql_insert(WarehouseBase.metadata.tables["professional_responses"]).values(
                response_id="resp_trung_1",
                work_item_id=work_item_id,
                version=1,
                etag="a",
                status="superseded",
                sections_json=[],
                assessment_status="insufficient_evidence",
                coverage_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

    state = inspect_state(legacy_db)
    assert "uq_response_version" in state["duplicate_keys"]
    assert any(
        name.startswith("uq_response_version")
        for name in state["missing_indexes"]["professional_responses"]
    )

    report = migrate(legacy_db)
    assert report["blocked"] is True
    assert report["created_indexes"] == []
    # Vẫn thiếu chỉ mục (chưa tạo), nhưng không nổ giữa đường và dữ liệu còn nguyên.
    assert store.counts()["professional_responses"] == 2


def test_over_length_inputs_are_rejected_before_the_database(legacy_db):
    """Đầu vào quá dài phải trả 422; để cơ sở dữ liệu nổ là lỗi hệ thống (DataError)."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(question="Câu hỏi")

    calls = {
        "work_item_id": lambda: store.create_work_item(question="Câu hỏi", work_item_id="w" * 81),
        "revision_of": lambda: store.create_work_item(question="Câu hỏi", revision_of="w" * 81),
        "revision_reason": lambda: store.create_work_item(question="Câu hỏi", revision_reason="x" * 301),
        "update reason": lambda: store.update_work_item(
            created["work_item_id"], changes={"priority": "urgent"}, expected_version=1, reason="x" * 301
        ),
        "response_id": lambda: store.save_response(
            created["work_item_id"], sections=[{"key": "summary", "text": "Nội dung."}], response_id="r" * 81
        ),
        "investigation_id": lambda: store.add_investigation_link(
            created["work_item_id"], investigation_id="i" * 121
        ),
        "follow_up_id": lambda: store.add_follow_up(
            created["work_item_id"], kind="recheck_source", note="Ghi chú.", follow_up_id="f" * 81
        ),
    }
    for label, call in calls.items():
        with pytest.raises(MvpError) as too_long:
            call()
        assert too_long.value.code == ErrorCode.INVALID_REQUEST, label


def test_empty_identifier_is_rejected_instead_of_being_replaced(legacy_db):
    """Mã rỗng là đầu vào sai, không được lặng lẽ thay bằng mã mới sinh."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    created = store.create_work_item(question="Câu hỏi")

    calls = (
        lambda: store.create_work_item(question="Câu hỏi", work_item_id=""),
        lambda: store.save_response(
            created["work_item_id"], sections=[{"key": "summary", "text": "Nội dung."}], response_id=""
        ),
        lambda: store.add_investigation_link(created["work_item_id"], investigation_id="inv-1", link_id=""),
        lambda: store.add_follow_up(created["work_item_id"], kind="recheck_source", note="Ghi chú.", follow_up_id=""),
        lambda: store.add_evidence_bundle(
            created["work_item_id"],
            investigation_id="inv-1",
            items=[{"source": "pubmed", "identifier": "1"}],
            gaps=[],
            coverage={"queries": 1},
            assessment_status="insufficient_evidence",
            bundle_id="",
        ),
    )
    for call in calls:
        with pytest.raises(MvpError) as empty_id:
            call()
        assert empty_id.value.code == ErrorCode.INVALID_REQUEST


def test_duplicate_response_id_is_reported_as_a_conflict(legacy_db):
    """Mã phiếu trùng phải báo ``IDEMPOTENCY_CONFLICT`` như mọi mã trùng khác."""
    migrate(legacy_db)
    store = CaseWorkStore(legacy_db)
    work_item_id = store.create_work_item(question="Câu hỏi")["work_item_id"]
    store.save_response(work_item_id, sections=[{"key": "summary", "text": "Bản đầu."}], response_id="resp-1")

    with pytest.raises(MvpError) as duplicate:
        store.save_response(
            work_item_id, sections=[{"key": "summary", "text": "Bản khác."}], response_id="resp-1"
        )
    assert duplicate.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_response_save_conflict_covers_both_unique_constraints():
    """Bên thua trong đua lưu phiếu nhận *cùng một* lỗi dù ràng buộc nào chặn nó.

    Ràng buộc số phiên bản và ràng buộc "một bản hiện hành" bắt hai tình huống khác nhau
    của cùng một cuộc đua; mã lỗi không được phụ thuộc vào việc ràng buộc nào bắt được.
    """
    from src.services.casework.store import _response_save_conflicts

    conflicts = _response_save_conflicts("wi_1", 3)
    assert set(conflicts) == {"uq_response_version", "uq_response_current"}
    assert len(set(map(id, conflicts.values()))) == 1
    only = next(iter(conflicts.values()))
    assert only.code == ErrorCode.INVALID_STATE
    assert only.details == {"work_item_id": "wi_1", "attempted_version": 3}
