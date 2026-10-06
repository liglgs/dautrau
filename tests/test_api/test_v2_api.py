"""R2-2-02: chín điểm cuối ``/api/v2`` trên lát cắt DI.

Chạy ngoại tuyến trên SQLite qua ``app.dependency_overrides`` — cùng cách ``test_casework_store.py``
kiểm tầng lưu trữ. Điều đáng kiểm ở đây không phải "tuyến có trả 200" mà là bốn quy tắc dễ vi phạm:

* ba trạng thái (nghiệp vụ / chạy / duyệt) **không** suy ra nhau;
* ca ngoài phạm vi trả **404**, không phải 403 — không dò được ca có tồn tại;
* ghi mà thiếu ``expected_version`` nhận **422**, ghi thua cuộc đua nhận **409** kèm bản hiện tại;
* phiếu trả lời **luôn** sinh ra ở dạng nháp; chỉ ``review:decide`` mới đổi được trạng thái.
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.v2_routes import get_casework_store
from src.main import app
from src.services.casework.store import CaseWorkStore
from src.services.warehouse.db import get_warehouse_engine


def _headers(role: str, user_id: str | None = None) -> dict[str, str]:
    return {"X-Test-User": f"{user_id or f'usr_{role}'}:{role}"}


@pytest_asyncio.fixture
async def v2_client(tmp_path):
    engine = get_warehouse_engine(f"sqlite:///{tmp_path / 'v2.db'}")
    store = CaseWorkStore(engine)
    app.dependency_overrides[get_casework_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_casework_store, None)


def _body(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "question": "Metformin có gây nhiễm toan lactic ở người suy thận giai đoạn 3b không?",
        "context": {
            "requester": {"id": "usr_investigator", "display_name": "Điều tra viên A"},
            "channel": "api",
            "raw_text": "Metformin có gây nhiễm toan lactic ở người suy thận giai đoạn 3b không?",
            "language": "vi",
        },
        "priority": "routine",
    }
    values.update(overrides)
    return values


async def _create(client: AsyncClient, role: str = "investigator", **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v2/work-items", json=_body(**overrides), headers=_headers(role))
    assert response.status_code == 201, response.text
    return response.json()


# ------------------------------------------------------------------ tiếp nhận và đọc


@pytest.mark.asyncio
async def test_create_work_item_starts_as_a_draft(v2_client):
    """Tiếp nhận **không** đồng nghĩa với bắt đầu điều tra."""
    document = await _create(v2_client)
    assert document["work_status"] == "draft"
    assert document["run_status"] == "not_started"
    assert document["review_status"] == "not_required"
    assert document["version"] == 1
    assert document["investigation_ids"] == []


@pytest.mark.asyncio
async def test_request_id_and_received_at_are_minted_by_the_server(v2_client):
    """Nhật ký truy vết dựa vào hai trường này, nên người gọi không được tự đặt."""
    document = await _create(v2_client)
    assert document["context"]["request_id"]
    assert document["context"]["received_at"]

    forged = _body()
    forged["context"]["request_id"] = "req-tu-nghi"
    forged["context"]["received_at"] = "2000-01-01T00:00:00Z"
    response = await v2_client.post("/api/v2/work-items", json=forged, headers=_headers("investigator"))
    assert response.status_code == 422
    assert "extra_forbidden" in response.text or "extra" in response.text


@pytest.mark.asyncio
async def test_list_shows_only_your_own_items(v2_client):
    """Người chỉ có ``read:own`` không được thấy ca người khác."""
    await _create(v2_client, "investigator")
    await _create(v2_client, "reviewer")

    mine = await v2_client.get("/api/v2/work-items", headers=_headers("investigator"))
    assert mine.status_code == 200
    assert len(mine.json()["items"]) == 1

    everything = await v2_client.get("/api/v2/work-items", headers=_headers("reviewer"))
    assert len(everything.json()["items"]) == 2


@pytest.mark.asyncio
async def test_reading_another_persons_item_is_404_not_403(v2_client):
    """404 để không dò được ca có tồn tại."""
    created = await _create(v2_client, "investigator", owner={"id": "usr_investigator"})
    # Người điều tra thứ hai không có ``read:any``, nên ca này nằm ngoài phạm vi của họ.
    response = await v2_client.get(
        f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator", "usr_khac")
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_reading_your_own_item_returns_the_bundle(v2_client):
    created = await _create(v2_client, "investigator", owner={"id": "usr_investigator"})
    response = await v2_client.get(
        f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator", "usr_investigator")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["work_item"]["work_item_id"] == created["work_item_id"]
    assert body["investigation_links"] == [] and body["responses"] == []


@pytest.mark.asyncio
async def test_unknown_field_is_rejected(v2_client):
    response = await v2_client.post(
        "/api/v2/work-items", json=_body(drug="metformin"), headers=_headers("investigator")
    )
    assert response.status_code == 422


# ------------------------------------------------------------------ sửa và khoá lạc quan


@pytest.mark.asyncio
async def test_patch_without_expected_version_is_422(v2_client):
    """Thiếu khoá thì không được hiểu ngầm là "ghi đè bản mới nhất"."""
    created = await _create(v2_client)
    response = await v2_client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"priority": "urgent"},
        headers=_headers("investigator"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_bumps_the_version(v2_client):
    created = await _create(v2_client)
    response = await v2_client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "priority": "urgent", "work_status": "accepted"},
        headers=_headers("investigator"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["priority"] == "urgent"
    assert body["work_status"] == "accepted"
    assert body["version"] == created["version"] + 1
    assert body["etag"] == response.headers["etag"]


@pytest.mark.asyncio
async def test_patch_with_a_stale_version_is_409_with_the_current_row(v2_client):
    created = await _create(v2_client)
    first = await v2_client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "priority": "urgent"},
        headers=_headers("investigator"),
    )
    assert first.status_code == 200

    stale = await v2_client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "priority": "stat"},
        headers=_headers("investigator"),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "version_conflict"
    # Trạng thái hiện tại phải có trong lỗi để giao diện vẽ lại, không phải đoán.
    assert stale.json()["error"]["details"]["current_version"] == created["version"] + 1


@pytest.mark.asyncio
async def test_reassigning_the_owner_needs_queue_assign(v2_client):
    """Gán chủ sở hữu là việc của hàng đợi, không phải của người điều tra."""
    created = await _create(v2_client, "investigator", owner={"id": "usr_investigator"})
    denied = await v2_client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "owner": {"id": "usr_khac"}},
        headers=_headers("investigator", "usr_investigator"),
    )
    assert denied.status_code == 403

    allowed = await v2_client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "owner": {"id": "usr_khac"}},
        headers=_headers("reviewer"),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["owner"]["id"] == "usr_khac"


# ------------------------------------------------------------------ lần chạy và gói bằng chứng


@pytest.mark.asyncio
async def test_linking_an_investigation_records_the_purpose(v2_client):
    """Một yêu cầu có thể có nhiều lần chạy; chúng không được lẫn vào nhau."""
    created = await _create(v2_client)
    response = await v2_client.post(
        f"/api/v2/work-items/{created['work_item_id']}/investigations",
        json={"investigation_id": "INV-abc", "purpose": "initial", "state": "queued"},
        headers=_headers("investigator"),
    )
    assert response.status_code == 201, response.text
    link = response.json()
    assert link["purpose"] == "initial"
    assert link["state"] == "queued"

    again = await v2_client.post(
        f"/api/v2/work-items/{created['work_item_id']}/investigations",
        json={"investigation_id": "INV-def", "purpose": "recheck"},
        headers=_headers("investigator"),
    )
    assert again.json()["purpose"] == "recheck"

    bundle = await v2_client.get(
        f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator")
    )
    assert sorted(item["purpose"] for item in bundle.json()["investigation_links"]) == ["initial", "recheck"]


@pytest.mark.asyncio
async def test_evidence_bundle_before_any_run_is_404_not_an_empty_bundle(v2_client):
    """Gói rỗng trông y hệt "đã tìm mà không thấy gì" — đó là hai chuyện khác nhau."""
    created = await _create(v2_client)
    response = await v2_client.get(
        f"/api/v2/work-items/{created['work_item_id']}/evidence-bundle", headers=_headers("investigator")
    )
    assert response.status_code == 404
    assert response.json()["error"]["details"]["remedy"]


# ------------------------------------------------------------------ phiếu trả lời


async def _make_response(client: AsyncClient, created: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Chưa đủ bằng chứng.", "citations": []}],
            "assessment_status": "insufficient_evidence",
        },
        headers=_headers("investigator"),
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_a_new_response_is_always_a_draft(v2_client):
    created = await _create(v2_client)
    document = await _make_response(v2_client, created)
    assert document["status"] == "draft"
    assert document["version"] == 1
    assert document["review"] is None


@pytest.mark.asyncio
async def test_a_new_response_supersedes_the_previous_one(v2_client):
    """Bản cũ chuyển sang ``superseded`` chứ không bị xoá, để còn đối chiếu đã đổi gì."""
    created = await _create(v2_client)
    first = await _make_response(v2_client, created)
    second = await _make_response(v2_client, created)

    assert second["supersedes"] == first["response_id"]
    older = await v2_client.get(
        f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator")
    )
    statuses = {item["response_id"]: item["status"] for item in older.json()["responses"]}
    assert statuses[first["response_id"]] == "superseded"
    assert statuses[second["response_id"]] == "draft"


@pytest.mark.asyncio
async def test_only_a_reviewer_can_decide(v2_client):
    created = await _create(v2_client)
    document = await _make_response(v2_client, created)

    denied = await v2_client.post(
        f"/api/v2/responses/{document['response_id']}/review",
        json={"action": "approve"},
        headers=_headers("investigator"),
    )
    assert denied.status_code == 403

    allowed = await v2_client.post(
        f"/api/v2/responses/{document['response_id']}/review",
        json={"action": "approve", "reason": "Bằng chứng khớp phạm vi.", "expected_version": document["version"]},
        headers=_headers("reviewer"),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_request_changes_keeps_the_response_out_of_approved(v2_client):
    created = await _create(v2_client)
    document = await _make_response(v2_client, created)
    response = await v2_client.post(
        f"/api/v2/responses/{document['response_id']}/review",
        json={
            "action": "request_changes",
            "reason": "Thiếu phạm vi dân số.",
            "expected_version": document["version"],
        },
        headers=_headers("reviewer"),
    )
    assert response.status_code == 200
    # ``RESPONSE_REVIEW_TARGET`` trong kho đưa phiếu trả lời về ``draft`` khi bị yêu cầu sửa: phiếu
    # quay lại cho người soạn, chứ không có trạng thái "chờ sửa" riêng. Điều bắt buộc là nó **không**
    # được thành ``approved``.
    assert response.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_reviewing_an_unknown_response_is_404(v2_client):
    response = await v2_client.post(
        "/api/v2/responses/RSP-khong-co/review",
        json={"action": "approve", "expected_version": 1},
        headers=_headers("reviewer"),
    )
    assert response.status_code == 404


# ------------------------------------------------------------------ việc theo dõi


@pytest.mark.asyncio
async def test_follow_up_does_not_invent_a_deadline(v2_client):
    """Hệ thống không biết hạn luật định nào áp dụng cho cơ sở nào, nên không tự đặt."""
    created = await _create(v2_client)
    response = await v2_client.post(
        f"/api/v2/work-items/{created['work_item_id']}/follow-ups",
        json={"kind": "request_information", "note": "Xin bệnh án chi tiết hơn."},
        headers=_headers("investigator"),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["due_at"] is None
    assert body["status"] == "open"


@pytest.mark.asyncio
async def test_a_bad_due_at_is_rejected(v2_client):
    created = await _create(v2_client)
    response = await v2_client.post(
        f"/api/v2/work-items/{created['work_item_id']}/follow-ups",
        json={"kind": "monitor_case", "note": "Theo dõi.", "due_at": "ngày mai"},
        headers=_headers("investigator"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_every_endpoint_rejects_an_unauthenticated_call(v2_client):
    """Không có danh tính thì không tuyến nào được trả dữ liệu."""
    calls = [
        ("post", "/api/v2/work-items", _body()),
        ("get", "/api/v2/work-items", None),
        ("get", "/api/v2/work-items/WI-1", None),
        ("patch", "/api/v2/work-items/WI-1", {"expected_version": 1, "priority": "urgent"}),
        ("post", "/api/v2/work-items/WI-1/investigations", {"investigation_id": "INV-1"}),
        ("get", "/api/v2/work-items/WI-1/evidence-bundle", None),
        ("post", "/api/v2/work-items/WI-1/responses", {"sections": [], "assessment_status": "insufficient_evidence"}),
        ("post", "/api/v2/responses/RSP-1/review", {"action": "approve", "expected_version": 1}),
        ("post", "/api/v2/work-items/WI-1/follow-ups", {"kind": "close", "note": "x"}),
    ]
    for method, path, payload in calls:
        response = await getattr(v2_client, method)(path, json=payload) if payload else await getattr(
            v2_client, method
        )(path)
        assert response.status_code == 401, f"{method.upper()} {path} → {response.status_code}"
