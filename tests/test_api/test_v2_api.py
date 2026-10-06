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
from sqlalchemy import text

from src.api.v2_routes import get_casework_store
from src.main import app
from src.models.schemas import ErrorCode
from src.services.casework.models import EvidenceBundle
from src.services.casework.store import CaseWorkStore
from src.services.errors import MvpError
from src.services.warehouse.db import get_warehouse_engine, session_scope
from src.services.warehouse.models import now


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


@pytest_asyncio.fixture
async def v2_client_with_store(tmp_path):
    """Như ``v2_client`` nhưng trả thêm kho, cho bài cần chỉnh dữ liệu nền."""
    engine = get_warehouse_engine(f"sqlite:///{tmp_path / 'v2b.db'}")
    store = CaseWorkStore(engine)
    app.dependency_overrides[get_casework_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, store
    app.dependency_overrides.pop(get_casework_store, None)


def _body(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "question": "Metformin có gây nhiễm toan lactic ở người suy thận giai đoạn 3b không?",
        "context": {
            "requester": {"id": "usr_investigator"},
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
async def test_the_queue_does_not_hide_your_item_behind_other_peoples(v2_client_with_store):
    """Lọc phạm vi phải nằm **trong câu truy vấn**, không cắt trang trước rồi lọc sau.

    Hàng đợi sắp theo thời điểm toàn kho. Cắt trang trước thì ca của chính người gọi bị chôn dưới
    ca của người khác và không trang nào chạm tới nữa (đã tái hiện trên PostgreSQL: ``items: []``
    kèm ``next_cursor: null``). Bài này khoá lại thứ tự bằng cách đẩy ca của người khác lên tương
    lai, để kết quả không phụ thuộc độ phân giải đồng hồ.
    """
    client, store = v2_client_with_store
    mine = await _create(client, "investigator", owner={"id": "usr_investigator"})
    for index in range(3):
        await _create(client, "reviewer", owner={"id": f"usr_khac_{index}"})
    with store.engine.begin() as connection:
        connection.execute(
            text("UPDATE work_items SET created_at = '2099-01-01 00:00:00' WHERE work_item_id != :mine"),
            {"mine": mine["work_item_id"]},
        )

    page = await client.get(
        "/api/v2/work-items?limit=1", headers=_headers("investigator", "usr_investigator")
    )
    assert page.status_code == 200, page.text
    assert [item["work_item_id"] for item in page.json()["items"]] == [mine["work_item_id"]], page.text

    # Và không được lộ ca của người khác qua danh sách.
    assert all(item["owner"]["id"] == "usr_investigator" for item in page.json()["items"])


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
            "coverage": {
                "documents_retrieved": 1,
                "sources_ok": ["pubmed"],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": True,
            },
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
        (
            "post",
            "/api/v2/work-items/WI-1/responses",
            {
                "sections": [],
                "assessment_status": "insufficient_evidence",
                "coverage": {
                    "documents_retrieved": 0,
                    "sources_ok": [],
                    "sources_empty": [],
                    "sources_error": [],
                    "abstract_only": False,
                },
            },
        ),
        ("post", "/api/v2/responses/RSP-1/review", {"action": "approve", "expected_version": 1}),
        ("post", "/api/v2/work-items/WI-1/follow-ups", {"kind": "close", "note": "x"}),
    ]
    for method, path, payload in calls:
        response = await getattr(v2_client, method)(path, json=payload) if payload else await getattr(
            v2_client, method
        )(path)
        assert response.status_code == 401, f"{method.upper()} {path} → {response.status_code}"


# --------------------------------------------------------------------------------------
# Vòng rà soát `e917b7b`: bốn phát hiện được sửa, mỗi phát hiện có bài khoá lại
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paging_reaches_items_past_the_page_cap(v2_client_with_store):
    """``limit`` chạm trần vẫn phải còn con trỏ sang trang sau.

    Bản trước lấy dư một dòng (``limit + 1``) để đoán còn trang hay không, nhưng kho kẹp ``limit``
    về trần nên ở ``limit`` bằng trần thì dòng dư biến mất và ``next_cursor`` luôn là ``null`` —
    các ca từ 201 trở đi không đường nào tới được, kể cả với người có ``read:any``.
    """
    client, store = v2_client_with_store
    for index in range(205):
        store.create_work_item(question=f"Câu hỏi {index}", owner={"id": "usr_reviewer"})

    first = await client.get("/api/v2/work-items?limit=200", headers=_headers("reviewer"))
    assert first.status_code == 200, first.text
    body = first.json()
    assert len(body["items"]) == 200
    assert body["total"] == 205
    assert body["next_cursor"] == "200", body

    second = await client.get(f"/api/v2/work-items?limit=200&cursor={body['next_cursor']}", headers=_headers("reviewer"))
    assert second.status_code == 200, second.text
    assert len(second.json()["items"]) == 5
    assert second.json()["next_cursor"] is None


@pytest.mark.asyncio
async def test_total_counts_the_whole_queue_not_the_page(v2_client):
    """``total`` là số ca khớp bộ lọc, không phải số dòng của trang này."""
    client = v2_client
    for _ in range(4):
        await _create(client)

    page = await client.get("/api/v2/work-items?limit=2", headers=_headers("investigator"))
    assert page.status_code == 200, page.text
    assert len(page.json()["items"]) == 2
    assert page.json()["total"] == 4
    assert page.json()["next_cursor"] == "2"


@pytest.mark.asyncio
async def test_the_reviewer_is_the_caller_not_a_name_in_the_body(v2_client_with_store):
    """Không ai ký được quyết định duyệt dưới tên người khác.

    Bản trước nhận ``reviewer`` từ thân yêu cầu, nên một yêu cầu xác thực bằng tài khoản A vẫn ghi
    được quyết định dưới mã người B — phá đúng thứ mà dấu duyệt dùng để làm bằng chứng.
    """
    client, store = v2_client_with_store
    created = await _create(client, "investigator")
    document = await _make_response(client, created)

    forged = await client.post(
        f"/api/v2/responses/{document['response_id']}/review",
        json={
            "action": "approve",
            "expected_version": document["version"],
            "reviewer": {"id": "usr_nguoi_khac"},
        },
        headers=_headers("reviewer", "usr_nguoi_duyet_that"),
    )
    assert forged.status_code == 422, forged.text

    allowed = await client.post(
        f"/api/v2/responses/{document['response_id']}/review",
        json={"action": "approve", "expected_version": document["version"]},
        headers=_headers("reviewer", "usr_nguoi_duyet_that"),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["review"]["reviewer"]["id"] == "usr_nguoi_duyet_that"
    reviews = store.list_reviews(entity="response", entity_id=document["response_id"])
    assert [row["reviewer"]["id"] for row in reviews] == ["usr_nguoi_duyet_that"]


@pytest.mark.asyncio
async def test_the_drafter_is_the_caller_not_a_name_in_the_body(v2_client):
    """Người soạn phiếu cũng do máy chủ điền, không nhận từ thân yêu cầu."""
    client = v2_client
    created = await _create(client, "investigator")
    response = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "drafted_by": {"id": "usr_nguoi_khac"},
            "coverage": {
                "documents_retrieved": 1,
                "sources_ok": ["pubmed"],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": True,
            },
        },
        headers=_headers("investigator", "usr_nguoi_soan_that"),
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_creating_a_case_for_someone_else_needs_queue_assign(v2_client):
    """Giao ca cho người khác là việc của hàng đợi, không phải của người điều tra.

    Không chặn thì người điều tra tự đẩy ca của mình sang người khác rồi **mất luôn quyền đọc**
    chính ca đó (không có ``read:any``), mà nhật ký vẫn ghi như một thao tác bình thường.
    """
    client = v2_client

    async def post(role: str, **overrides: Any):
        return await client.post("/api/v2/work-items", json=_body(**overrides), headers=_headers(role))

    denied = await post("investigator", owner={"id": "usr_nguoi_khac"})
    assert denied.status_code == 403, denied.text
    assert "queue:assign" in denied.text

    allowed = await post("reviewer", owner={"id": "usr_nguoi_khac"})
    assert allowed.status_code == 201, allowed.text

    mine = await post("investigator", owner={"id": "usr_investigator"})
    assert mine.status_code == 201, mine.text


@pytest.mark.asyncio
async def test_handing_a_follow_up_to_someone_else_needs_queue_assign(v2_client):
    """Cùng luật với ``owner``: nêu tên người khác trong ``assignee`` đòi ``queue:assign``."""
    client = v2_client
    created = await _create(client, "investigator")
    denied = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/follow-ups",
        json={"kind": "handover", "note": "Chuyển ca.", "assignee": {"id": "usr_nguoi_khac"}},
        headers=_headers("investigator"),
    )
    assert denied.status_code == 403, denied.text

    own = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/follow-ups",
        json={"kind": "handover", "note": "Tự nhận.", "assignee": {"id": "usr_investigator"}},
        headers=_headers("investigator"),
    )
    assert own.status_code == 201, own.text


@pytest.mark.asyncio
async def test_a_new_case_cannot_be_opened_already_closed(v2_client):
    """Yêu cầu mới luôn ở ``draft``; không có đường tắt tạo thẳng ca đã duyệt hay đã huỷ."""
    client = v2_client
    for state in ("completed", "cancelled", "in_review"):
        response = await client.post(
            "/api/v2/work-items", json=_body(work_status=state), headers=_headers("investigator")
        )
        assert response.status_code == 422, f"{state}: {response.text}"

    draft = await _create(client, "investigator")
    assert draft["work_status"] == "draft"


@pytest.mark.asyncio
async def test_an_owner_can_be_cleared_back_to_the_requester(v2_client):
    """``owner: null`` là xoá chủ sở hữu, khác hẳn với không gửi trường đó."""
    client = v2_client
    created = await _create(client, "reviewer", owner={"id": "usr_nguoi_khac"})
    assert created["owner"]["id"] == "usr_nguoi_khac"

    cleared = await client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "owner": None},
        headers=_headers("reviewer"),
    )
    assert cleared.status_code == 200, cleared.text
    assert not cleared.json()["owner"]

    omitted = await client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": cleared.json()["version"], "priority": "urgent"},
        headers=_headers("reviewer"),
    )
    assert omitted.status_code == 200, omitted.text
    assert not omitted.json()["owner"]


@pytest.mark.asyncio
async def test_linking_a_run_leaves_the_work_status_alone(v2_client):
    """Ba trạng thái không suy ra nhau: liên kết một lần chạy không đổi trạng thái nghiệp vụ."""
    client = v2_client
    created = await _create(client, "investigator")
    linked = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/investigations",
        json={"investigation_id": "INV-1", "purpose": "initial", "state": "running"},
        headers=_headers("investigator"),
    )
    assert linked.status_code == 201, linked.text

    read = await client.get(f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator"))
    assert read.json()["work_item"]["work_status"] == "draft"
    assert read.json()["investigation_links"][0]["state"] == "running"


@pytest.mark.asyncio
async def test_the_etag_is_a_quoted_entity_tag(v2_client):
    """``ETag`` gửi đi phải đúng cú pháp HTTP, nếu không ``If-Match`` của khách hàng chuẩn không khớp."""
    client = v2_client
    response = await client.post("/api/v2/work-items", json=_body(), headers=_headers("investigator"))
    assert response.status_code == 201, response.text
    etag = response.headers["ETag"]
    assert etag.startswith('W/"') and etag.endswith('"'), etag
    assert response.json()["etag"] in etag


@pytest.mark.asyncio
async def test_the_approval_decision_comes_back_with_the_response(v2_client):
    """Duyệt xong phải thấy được dấu duyệt ngay, khỏi gọi thêm một vòng đọc."""
    client = v2_client
    created = await _create(client, "investigator")
    document = await _make_response(client, created)
    reviewed = await client.post(
        f"/api/v2/responses/{document['response_id']}/review",
        json={"action": "approve", "expected_version": document["version"]},
        headers=_headers("reviewer", "usr_nguoi_duyet"),
    )
    assert reviewed.status_code == 200, reviewed.text
    review = reviewed.json()["review"]
    assert review["action"] == "approve"
    assert review["reviewer"]["id"] == "usr_nguoi_duyet"
    assert review["previous_status"] == "draft"
    assert review["new_status"] == "approved"


@pytest.mark.asyncio
async def test_the_scope_is_a_valid_contract_object_even_when_the_caller_says_nothing(v2_client):
    """Không gửi phạm vi thì phạm vi vẫn hợp lệ: cả hai trường là "chưa rõ", không phải rỗng.

    Hợp đồng đòi ``scope`` có đủ ``drug`` và ``event``; ``resolution="unknown"`` là cách nói "chưa
    biết", khác hẳn với một đối tượng rỗng mà hợp đồng không cho phép.
    """
    client = v2_client
    document = await _create(client)
    assert document["scope"]["drug"]["resolution"] == "unknown"
    assert document["scope"]["event"]["resolution"] == "unknown"
    assert document["scope"]["drug"]["value"] is None


@pytest.mark.asyncio
async def test_the_scope_carries_what_the_caller_did_say(v2_client):
    """Nêu rõ phạm vi thì đi đúng vào tài liệu, kèm mức độ chắc chắn."""
    client = v2_client
    document = await _create(
        client,
        scope={
            "drug": {"value": "metformin", "resolution": "confirmed", "source": "requester"},
            "event": {"value": "nhiễm toan lactic", "resolution": "candidate"},
        },
    )
    # ``source`` có mặt vì người gọi nêu; ``evidence_ref`` **vắng hẳn** chứ không bằng ``null`` —
    # hợp đồng cho phép vắng trường tuỳ chọn nhưng không cho ``null``.
    assert document["scope"]["drug"] == {
        "value": "metformin",
        "resolution": "confirmed",
        "source": "requester",
    }
    assert "evidence_ref" not in document["scope"]["drug"]
    assert document["scope"]["event"]["resolution"] == "candidate"


@pytest.mark.asyncio
async def test_a_made_up_scope_resolution_is_rejected(v2_client):
    """Mức độ chắc chắn là một tập đóng; không nhận giá trị tự nghĩ ra."""
    client = v2_client
    response = await client.post(
        "/api/v2/work-items",
        json=_body(scope={"drug": {"value": "x", "resolution": "chac_chan"}, "event": {"resolution": "unknown"}}),
        headers=_headers("investigator"),
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_the_requester_is_an_actor_without_extra_fields(v2_client):
    """``Actor`` của hợp đồng không có ``display_name``; nhận thêm là làm hỏng tài liệu trả về."""
    client = v2_client
    forged = _body()
    forged["context"]["requester"] = {"id": "usr_investigator", "display_name": "Tên tự đặt"}
    response = await client.post("/api/v2/work-items", json=forged, headers=_headers("investigator"))
    assert response.status_code == 422, response.text

    invented_role = _body()
    invented_role["context"]["requester"] = {"id": "usr_investigator", "role": "trưởng khoa"}
    rejected = await client.post("/api/v2/work-items", json=invented_role, headers=_headers("investigator"))
    assert rejected.status_code == 422, rejected.text


@pytest.mark.asyncio
async def test_a_response_must_say_how_much_evidence_it_retrieved(v2_client):
    """Thiếu ``coverage`` là 422: phiếu nói "đã đối chiếu" mà không nói đối chiếu được bao nhiêu."""
    client = v2_client
    created = await _create(client, "investigator")
    response = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
        },
        headers=_headers("investigator"),
    )
    assert response.status_code == 422, response.text
    assert "coverage" in response.text


@pytest.mark.asyncio
async def test_lengths_follow_the_contract_not_the_router(v2_client):
    """Trần độ dài lấy từ hợp đồng: đoạn 8000 ký tự, ghi chú việc theo dõi 1000."""
    client = v2_client
    created = await _create(client, "investigator")

    long_section = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "x" * 8001, "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 0,
                "sources_ok": [],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": False,
            },
        },
        headers=_headers("investigator"),
    )
    assert long_section.status_code == 422, long_section.text

    long_note = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/follow-ups",
        json={"kind": "recheck_source", "note": "x" * 1001},
        headers=_headers("investigator"),
    )
    assert long_note.status_code == 422, long_note.text


@pytest.mark.asyncio
async def test_the_other_six_scope_fields_are_accepted_and_kept(v2_client):
    """Hợp đồng có **tám** trường phạm vi, không phải hai.

    Chỉ khai ``drug``/``event`` thì một yêu cầu hợp lệ có nêu dân số hay đường dùng bị trả 422, và
    B4.3 sẽ không có chỗ đặt sáu trường còn lại.
    """
    client = v2_client
    document = await _create(
        client,
        scope={
            "drug": {"value": "metformin", "resolution": "confirmed"},
            "event": {"value": "nhiễm toan lactic", "resolution": "candidate"},
            "population": {"value": "người suy thận giai đoạn 3b", "resolution": "confirmed"},
            "route": {"value": "uống", "resolution": "confirmed"},
            "dose": {"resolution": "unknown"},
            "time_window": {"value": "12 tuần", "resolution": "candidate"},
            "indication": {"value": "đái tháo đường týp 2", "resolution": "confirmed"},
            "comparator": {"resolution": "unknown"},
        },
    )
    scope = document["scope"]
    assert set(scope) == {
        "drug",
        "event",
        "population",
        "route",
        "dose",
        "time_window",
        "indication",
        "comparator",
    }
    assert scope["population"]["value"] == "người suy thận giai đoạn 3b"
    assert scope["comparator"] == {"value": None, "resolution": "unknown"}


@pytest.mark.asyncio
async def test_a_scope_field_never_carries_a_null_source(v2_client):
    """Trường tuỳ chọn của ``ScopeField`` vắng hẳn khi chưa biết, không mang giá trị ``null``."""
    client = v2_client
    document = await _create(client)
    for name in ("drug", "event"):
        assert set(document["scope"][name]) == {"value", "resolution"}, document["scope"][name]


@pytest.mark.asyncio
async def test_the_context_never_carries_a_null_optional_field(v2_client):
    """``Actor.role`` và ``source_system`` vắng hẳn khi chưa biết: hợp đồng cho vắng, không cho ``null``."""
    client = v2_client
    document = await _create(client)
    context = document["context"]
    assert set(context["requester"]) == {"id"}, context["requester"]
    assert "source_system" not in context
    assert context["request_id"] and context["received_at"]


@pytest.mark.asyncio
async def test_clearing_an_owner_is_a_queue_operation(v2_client):
    """Xoá chủ sở hữu cũng phải có ``queue:assign``.

    Không chặn thì người điều tra tạo ca với ``requester.id`` của người khác rồi xoá chủ sở hữu, và
    ca tự rơi vào hàng đợi của người đó — quyền ``queue:assign`` bị lách đúng bằng đường vòng.
    """
    client = v2_client
    created = await _create(client, "investigator")
    denied = await client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "owner": None},
        headers=_headers("investigator"),
    )
    assert denied.status_code == 403, denied.text

    allowed = await client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "owner": None},
        headers=_headers("reviewer"),
    )
    assert allowed.status_code == 200, allowed.text
    assert not allowed.json()["owner"]


@pytest.mark.asyncio
async def test_naming_someone_else_as_the_requester_needs_queue_assign(v2_client):
    """``context.requester`` cấp quyền đọc qua đường dự phòng, nên nêu tên người khác cũng là giao việc."""
    client = v2_client
    forged = _body()
    forged["context"]["requester"] = {"id": "usr_nguoi_khac"}
    denied = await client.post("/api/v2/work-items", json=forged, headers=_headers("investigator"))
    assert denied.status_code == 403, denied.text

    allowed = await client.post("/api/v2/work-items", json=forged, headers=_headers("reviewer"))
    assert allowed.status_code == 201, allowed.text

    self_named = _body()
    self_named["context"]["requester"] = {"id": "usr_investigator"}
    mine = await client.post("/api/v2/work-items", json=self_named, headers=_headers("investigator"))
    assert mine.status_code == 201, mine.text


@pytest.mark.asyncio
async def test_the_response_never_carries_a_null_coverage_list(v2_client):
    """``full_text_sources`` và ``note`` vắng hẳn khi chưa biết."""
    client = v2_client
    created = await _create(client, "investigator")
    response = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 1,
                "sources_ok": ["pubmed"],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": True,
            },
        },
        headers=_headers("investigator"),
    )
    assert response.status_code == 201, response.text
    coverage = response.json()["coverage"]
    assert "full_text_sources" not in coverage
    assert "note" not in coverage
    assert coverage["abstract_only"] is True


# ------------------------------------------------------------------ gói bằng chứng và hợp đồng


def _bundle(*, items: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> dict[str, Any]:
    """Tham số còn lại của ``add_evidence_bundle``, tách khỏi ``items``/``gaps`` để không truyền hai lần."""
    return {
        "investigation_id": "INV-bundle",
        "items": items,
        "gaps": gaps,
        "coverage": {
            "documents_retrieved": 1,
            "sources_ok": ["pubmed"],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": True,
        },
        "assessment_status": "insufficient_evidence",
    }


def _seed_unchecked_bundle(
    store,
    work_item_id: str,
    *,
    items: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    bundle_id: str = "eb_hong",
) -> str:
    """Gieo thẳng một gói sai lược đồ, **bỏ qua** cửa ghi của kho.

    Từ khi ``add_evidence_bundle`` tự soi hợp đồng thì không còn gieo được hàng hỏng qua đường
    công khai. Nhưng hàng hỏng đã lỡ nằm trong kho là chuyện thật — bản ghi cũ, hoặc một bên ghi
    khác — nên đường đọc vẫn phải được kiểm bằng dữ liệu như thế. Ghi thẳng qua ORM.
    """
    row = EvidenceBundle(
        bundle_id=bundle_id,
        work_item_id=work_item_id,
        investigation_id="INV-hong",
        created_at=now(),
        claim_json=None,
        items_json=items,
        gaps_json=gaps,
        coverage_json={
            "documents_retrieved": 1,
            "sources_ok": ["pubmed"],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": True,
        },
        assessment_status="insufficient_evidence",
        source_errors_json=[],
        limitations_json=[],
    )
    with session_scope(store.engine) as session:
        session.add(row)
    return bundle_id


_CONTRACT_ITEM = {
    "evidence_id": "EVI-1",
    "doc_id": "PMID-1",
    "source": "pubmed",
    "stance": "supports",
    "quote": "Trích đoạn nguyên văn.",
    "locator": {"start": 0, "end": 40, "section": "Tóm tắt"},
    "retrieval": "abstract_only",
}


@pytest.mark.asyncio
async def test_a_contract_shaped_bundle_comes_back(v2_client_with_store):
    """Gói đúng hợp đồng đi qua được, và đi qua nguyên vẹn."""
    client, store = v2_client_with_store
    created = await _create(client)
    store.add_evidence_bundle(
        created["work_item_id"],
        **_bundle(
            items=[dict(_CONTRACT_ITEM)],
            gaps=[{"kind": "missing_evidence", "detail": "Chưa có nhóm chứng."}],
        ),
    )
    response = await client.get(f"/api/v2/work-items/{created['work_item_id']}/evidence-bundle", headers=_headers("investigator"))
    assert response.status_code == 200, response.text
    document = response.json()
    assert document["items"][0]["stance"] == "supports"
    assert document["gaps"][0]["kind"] == "missing_evidence"


@pytest.mark.asyncio
async def test_a_bundle_that_breaks_the_contract_is_not_served(v2_client_with_store):
    """Gói sai lược đồ trả **500** kèm đường dẫn từng chỗ sai, không trả tài liệu hỏng.

    Tầng này là chỗ duy nhất tài liệu đi thẳng từ kho ra mà không qua một mô hình Pydantic nào, nên
    nếu không soi ở đây thì một khách hàng sinh kiểu từ hợp đồng sẽ đọc sai trường mà không có lỗi
    nào để lần theo.
    """
    client, store = v2_client_with_store
    created = await _create(client)
    _seed_unchecked_bundle(
        store,
        created["work_item_id"],
        items=[{"evidence_id": "EVI-1", "quote": "Thiếu doc_id, stance, locator, retrieval."}],
        gaps=[{"reason": "thiếu nhóm chứng"}],
    )
    response = await client.get(f"/api/v2/work-items/{created['work_item_id']}/evidence-bundle", headers=_headers("investigator"))
    assert response.status_code == 500, response.text
    body = response.json()
    assert body["error"]["code"] == "unavailable"
    violations = body["error"]["details"]["violations"]
    joined = " ".join(violations)
    assert "items/0" in joined and "doc_id" in joined
    assert "gaps/0" in joined and "kind" in joined


@pytest.mark.asyncio
async def test_a_bundle_that_is_missing_entirely_is_still_404(v2_client):
    """Chưa có gói nào vẫn là **404** — khác hẳn với "có gói nhưng gói hỏng"."""
    client = v2_client
    created = await _create(client)
    response = await client.get(f"/api/v2/work-items/{created['work_item_id']}/evidence-bundle", headers=_headers("investigator"))
    assert response.status_code == 404, response.text


# ------------------------------------------------------------------ ba trường trước đây cho qua nguyên xi


@pytest.mark.asyncio
async def test_the_source_system_must_say_whether_it_was_deidentified(v2_client):
    """``deidentified`` là trường **bắt buộc** của hợp đồng, không phải tuỳ chọn.

    Bỏ trống được thì hệ thống không phân biệt nổi một yêu cầu đã tách thông tin nhận dạng với một
    yêu cầu chưa ai kiểm.
    """
    client = v2_client
    missing = _body()
    missing["context"]["source_system"] = {"name": "his-bv-1"}
    denied = await client.post("/api/v2/work-items", json=missing, headers=_headers("investigator"))
    assert denied.status_code == 422, denied.text

    typed = _body()
    typed["context"]["source_system"] = {"name": "his-bv-1", "record_id": "HS-9", "deidentified": True}
    accepted = await client.post("/api/v2/work-items", json=typed, headers=_headers("investigator"))
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["context"]["source_system"]["deidentified"] is True

    unknown = _body()
    unknown["context"]["source_system"] = {"name": "his-bv-1", "deidentified": True, "ward": "A"}
    rejected = await client.post("/api/v2/work-items", json=unknown, headers=_headers("investigator"))
    assert rejected.status_code == 422, rejected.text


@pytest.mark.asyncio
async def test_an_attachment_ref_and_hash_follow_the_contract(v2_client):
    """``ref`` tối đa 500 ký tự, ``sha256`` phải đủ 64 ký tự thập lục phân, và không nhận khóa lạ."""
    client = v2_client
    too_long = _body()
    too_long["context"]["attachments"] = [{"kind": "file", "ref": "x" * 501}]
    assert (await client.post("/api/v2/work-items", json=too_long, headers=_headers("investigator"))).status_code == 422

    bad_hash = _body()
    bad_hash["context"]["attachments"] = [{"kind": "file", "ref": "hoso.pdf", "sha256": "khong-phai-bam"}]
    assert (await client.post("/api/v2/work-items", json=bad_hash, headers=_headers("investigator"))).status_code == 422

    bad_kind = _body()
    bad_kind["context"]["attachments"] = [{"kind": "gi-do", "ref": "hoso.pdf"}]
    assert (await client.post("/api/v2/work-items", json=bad_kind, headers=_headers("investigator"))).status_code == 422

    good = _body()
    good["context"]["attachments"] = [{"kind": "file", "ref": "hoso.pdf", "sha256": "a" * 64}]
    accepted = await client.post("/api/v2/work-items", json=good, headers=_headers("investigator"))
    assert accepted.status_code == 201, accepted.text


@pytest.mark.asyncio
async def test_the_run_summary_is_a_typed_object_not_a_free_dictionary(v2_client):
    """``run_summary`` đóng: số lượt là số nguyên không âm, không nhận khóa lạ."""
    client = v2_client
    created = await _create(client)
    url = f"/api/v2/work-items/{created['work_item_id']}/investigations"

    wrong_type = await client.post(
        url,
        json={"investigation_id": "INV-1", "run_summary": {"steps_used": "ba"}},
        headers=_headers("investigator"),
    )
    assert wrong_type.status_code == 422, wrong_type.text

    unknown_key = await client.post(
        url,
        json={"investigation_id": "INV-2", "run_summary": {"steps_used": 3, "ghi_chu": "thừa"}},
        headers=_headers("investigator"),
    )
    assert unknown_key.status_code == 422, unknown_key.text

    negative = await client.post(
        url,
        json={"investigation_id": "INV-3", "run_summary": {"steps_used": -1}},
        headers=_headers("investigator"),
    )
    assert negative.status_code == 422, negative.text

    accepted = await client.post(
        url,
        json={"investigation_id": "INV-4", "run_summary": {"steps_used": 3, "stop_reason": "du_budget"}},
        headers=_headers("investigator"),
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["run_summary"] == {"steps_used": 3, "stop_reason": "du_budget"}


# ------------------------------------------------------------------ trần độ dài và quyền qua PATCH


@pytest.mark.asyncio
async def test_the_contract_length_ceilings_are_enforced(v2_client):
    """Trần độ dài lấy theo hợp đồng, kiểm ở đúng hai bên biên."""
    client = v2_client
    headers = _headers("investigator")

    async def code(**overrides: Any) -> int:
        return (await client.post("/api/v2/work-items", json=_body(**overrides), headers=headers)).status_code

    at_ceiling = await code(
        context={
            "requester": {"id": "usr_investigator"},
            "channel": "api",
            "raw_text": "x" * 4000,
            "language": "vi",
        }
    )
    assert at_ceiling == 201, "4000 ký tự là mức hợp đồng cho phép"
    over = await code(
        context={
            "requester": {"id": "usr_investigator"},
            "channel": "api",
            "raw_text": "x" * 4001,
            "language": "vi",
        }
    )
    assert over == 422, "4001 ký tự phải bị chặn"

    assert await code(unknowns=[{"field": "x" * 80, "reason": "lý do"}]) == 201
    assert await code(unknowns=[{"field": "x" * 81, "reason": "lý do"}]) == 422
    assert await code(unknowns=[{"field": "lieu", "reason": "x" * 300}]) == 201
    assert await code(unknowns=[{"field": "lieu", "reason": "x" * 301}]) == 422
    assert await code(labels={"k": "x" * 80}) == 201
    assert await code(labels={"k": "x" * 81}) == 422
    assert await code(labels={"k": 7}) == 422, "nhãn phải là chuỗi, không phải số"


@pytest.mark.asyncio
async def test_the_coverage_note_ceiling_follows_the_contract(v2_client):
    """``coverage.note`` tối đa 400 ký tự."""
    client = v2_client
    created = await _create(client)
    url = f"/api/v2/work-items/{created['work_item_id']}/responses"

    def payload(note: str) -> dict[str, Any]:
        return {
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 1,
                "sources_ok": [],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": True,
                "note": note,
            },
        }

    assert (await client.post(url, json=payload("x" * 400), headers=_headers("investigator"))).status_code == 201
    assert (await client.post(url, json=payload("x" * 401), headers=_headers("investigator"))).status_code == 422


@pytest.mark.asyncio
async def test_claiming_your_own_case_needs_queue_assign_too(v2_client):
    """Mọi thay đổi ``owner`` đều là thao tác hàng đợi, kể cả khi người nhận là chính người gọi.

    Không phải luật thừa: ``owner`` là thứ **cấp quyền đọc**, nên "tự nhận ca" và "giao ca cho người
    khác" là cùng một thao tác. Người có ``queue:assign`` vẫn làm được, chỉ người không có mới bị chặn.
    """
    client = v2_client
    created = await _create(client, "investigator")
    denied = await client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "owner": {"id": "usr_investigator"}},
        headers=_headers("investigator"),
    )
    assert denied.status_code == 403, denied.text

    allowed = await client.patch(
        f"/api/v2/work-items/{created['work_item_id']}",
        json={"expected_version": created["version"], "owner": {"id": "usr_investigator"}},
        headers=_headers("reviewer"),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["owner"]["id"] == "usr_investigator"


@pytest.mark.asyncio
async def test_a_broken_bundle_is_not_served_through_the_work_item_either(v2_client_with_store):
    """Cùng một tài liệu thì cùng một luật: lớp bọc của `GET /work-items/{id}` cũng bị soi.

    Nếu chỉ soi ở đường đọc gói riêng thì chỗ dễ lách nhất lại là chỗ ít ai nhìn — giao diện đọc ca
    theo lớp bọc, nên đó mới là đường gói bằng chứng thật sự đi ra.
    """
    client, store = v2_client_with_store
    created = await _create(client)
    _seed_unchecked_bundle(
        store,
        created["work_item_id"],
        items=[{"evidence_id": "EVI-1", "quote": "Thiếu trường."}],
        gaps=[{"reason": "thiếu"}],
    )
    response = await client.get(f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator"))
    assert response.status_code == 500, response.text
    assert response.json()["error"]["code"] == "unavailable"

    # Đường liệt kê vẫn phải chạy: nó không trả nội dung gói, chỉ trả yêu cầu.
    listed = await client.get("/api/v2/work-items", headers=_headers("investigator"))
    assert listed.status_code == 200, listed.text


@pytest.mark.asyncio
async def test_the_last_decision_wins_even_when_the_clocks_match(v2_client_with_store):
    """Hai quyết định trùng dấu thời gian thì thứ tự thật là ``entity_version``, không phải mã ngẫu nhiên.

    Sắp theo ``review_id`` (mã ngẫu nhiên) làm "quyết định cuối" có thể hoá thành quyết định cũ — và
    đây là chỗ nói về việc một phiếu đã được duyệt hay chưa, nên sai một lần là sai một dấu duyệt.
    """
    client, store = v2_client_with_store
    created = await _create(client, "investigator")
    response = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 0,
                "sources_ok": [],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": False,
            },
        },
        headers=_headers("investigator"),
    )
    assert response.status_code == 201, response.text
    document = response.json()
    response_id = document["response_id"]

    first = store.add_review(
        entity="response",
        entity_id=response_id,
        action="request_changes",
        reviewer={"id": "usr_reviewer"},
        reason="Cần sửa.",
        expected_version=document["version"],
        review_id="rev_zzz_cu",
    )
    second = store.add_review(
        entity="response",
        entity_id=response_id,
        action="approve",
        reviewer={"id": "usr_reviewer"},
        reason="Đã sửa.",
        expected_version=document["version"] + 1,
        review_id="rev_aaa_moi",
    )
    assert first["entity_version"] < second["entity_version"]

    # Ép hai quyết định về cùng một dấu thời gian: đây là ca mà mã ngẫu nhiên sẽ chọn sai.
    with store.engine.begin() as connection:
        connection.execute(
            text("UPDATE review_refs SET decided_at = :when WHERE entity_id = :entity_id"),
            {"when": "2026-01-01 00:00:00+00:00", "entity_id": response_id},
        )

    stored = store.get_response(response_id)
    assert stored["review"]["action"] == "approve", "quyết định cuối phải thắng, không phải mã nhỏ hơn"
    assert stored["review"]["review_id"] == "rev_aaa_moi"

    envelope = await client.get(f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator"))
    assert envelope.status_code == 200, envelope.text
    assert envelope.json()["responses"][0]["review"]["action"] == "approve"


@pytest.mark.asyncio
async def test_a_slow_clock_cannot_outvote_the_real_write_order(v2_client_with_store):
    """``decided_at`` là giờ tường nên nó có thể lùi; thứ tự thật là ``entity_version``.

    Dựng đúng ca mà đồng hồ nói ngược: quyết định ghi **sau** mang dấu thời gian **sớm hơn**.
    Nếu ``decided_at`` còn đứng trước trong khoá sắp xếp thì bản cũ thắng, và người đọc ca thấy
    "yêu cầu sửa" trong khi phiếu đã được duyệt.
    """
    client, store = v2_client_with_store
    created = await _create(client, "investigator")
    response = await client.post(
        f"/api/v2/work-items/{created['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 0,
                "sources_ok": [],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": False,
            },
        },
        headers=_headers("investigator"),
    )
    assert response.status_code == 201, response.text
    document = response.json()
    response_id = document["response_id"]

    store.add_review(
        entity="response",
        entity_id=response_id,
        action="request_changes",
        reviewer={"id": "usr_reviewer"},
        reason="Cần sửa.",
        expected_version=document["version"],
        review_id="rev_cu",
    )
    store.add_review(
        entity="response",
        entity_id=response_id,
        action="approve",
        reviewer={"id": "usr_reviewer"},
        reason="Đã sửa xong.",
        expected_version=document["version"] + 1,
        review_id="rev_moi",
    )

    # Đồng hồ chậm: bản ghi sau nhận dấu thời gian sớm hơn bản ghi trước.
    with store.engine.begin() as connection:
        connection.execute(
            text("UPDATE review_refs SET decided_at = :when WHERE review_id = :review_id"),
            {"when": "2026-01-02 00:00:00+00:00", "review_id": "rev_cu"},
        )
        connection.execute(
            text("UPDATE review_refs SET decided_at = :when WHERE review_id = :review_id"),
            {"when": "2026-01-01 00:00:00+00:00", "review_id": "rev_moi"},
        )

    stored = store.get_response(response_id)
    assert stored["review"]["review_id"] == "rev_moi", "giờ tường không được đè lên thứ tự ghi thật"
    assert stored["review"]["action"] == "approve"

    envelope = await client.get(f"/api/v2/work-items/{created['work_item_id']}", headers=_headers("investigator"))
    assert envelope.status_code == 200, envelope.text
    assert envelope.json()["responses"][0]["review"]["action"] == "approve"


@pytest.mark.asyncio
async def test_two_decisions_on_a_bundle_do_not_share_a_version(v2_client_with_store):
    """Gói bằng chứng không có cột phiên bản, nên số phiên bản phải do số quyết định đếm ra.

    Gán cứng 1 thì hai quyết định hoà ở khoá giữa và thứ tự rơi xuống ``review_id`` ngẫu nhiên —
    tức là chọn sai bản cũ. Đường này hiện chưa tuyến nào gọi tới, nhưng ``add_review`` là cửa công
    khai nên bất biến phải đúng ở đó, không phải đúng nhờ may.
    """
    client, store = v2_client_with_store
    created = await _create(client, "investigator")
    bundle = store.add_evidence_bundle(
        created["work_item_id"],
        investigation_id="inv_bundle_order",
        items=[],
        gaps=[],
        coverage={
            "documents_retrieved": 0,
            "sources_ok": [],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": False,
        },
        assessment_status="insufficient_evidence",
    )

    first = store.add_review(
        entity="evidence_bundle",
        entity_id=bundle["bundle_id"],
        action="approve",
        reviewer={"id": "usr_reviewer"},
        review_id="rev_zzz_cu",
    )
    second = store.add_review(
        entity="evidence_bundle",
        entity_id=bundle["bundle_id"],
        action="reject",
        reviewer={"id": "usr_reviewer"},
        review_id="rev_aaa_moi",
    )
    assert (first["entity_version"], second["entity_version"]) == (1, 2)
    assert second["entity_version"] > first["entity_version"]


# ------------------------------------------------------------------ cửa ghi và gói cũ hỏng


@pytest.mark.asyncio
async def test_the_write_gate_refuses_a_bundle_that_breaks_the_contract(v2_client_with_store):
    """Cửa ghi tự soi hợp đồng: hàng sai không vào được kho thì không có gì phải dọn về sau.

    Không có tuyến nào xoá hay thay gói bằng chứng, nên chặn ở cửa ghi là chặn duy nhất có tác dụng
    thật. Soi ở cửa đọc là cần nhưng không đủ: nó chỉ phát hiện hàng hỏng, không ngăn được hàng hỏng.
    """
    client, store = v2_client_with_store
    created = await _create(client)
    with pytest.raises(MvpError) as bad:
        store.add_evidence_bundle(
            created["work_item_id"],
            **_bundle(items=[{"evidence_id": "EVI-1", "quote": "Thiếu trường."}], gaps=[]),
        )
    assert bad.value.code == ErrorCode.INVALID_REQUEST
    assert bad.value.status == 422
    joined = " ".join(bad.value.details["violations"])
    assert "items/0" in joined and "doc_id" in joined

    # Và không có gì được ghi lại: kiểm bằng chính kho, không tin lời hứa của mã.
    assert store.list_evidence_bundles(created["work_item_id"]) == []


@pytest.mark.asyncio
async def test_an_old_broken_bundle_is_dropped_instead_of_killing_the_case(v2_client_with_store):
    """Gói **cũ** hỏng bị gỡ ra kèm danh sách, thay vì làm cả ca bệnh trả 500 vĩnh viễn.

    Trước đây một dòng lịch sử hỏng làm ``GET /work-items/{id}`` đổ mãi mãi, kể cả khi gói mới nhất
    đã đúng, và không có đường sửa nào — hồ sơ mất hẳn chứ không phải chỉ thiếu một mục. Gói cũ là
    lịch sử, không phải câu trả lời, nên nó không được quyền treo cả ca.
    """
    client, store = v2_client_with_store
    created = await _create(client)
    work_item_id = created["work_item_id"]
    _seed_unchecked_bundle(
        store,
        work_item_id,
        items=[{"evidence_id": "EVI-1", "quote": "Thiếu doc_id, stance, locator, retrieval."}],
        gaps=[{"reason": "thiếu nhóm chứng"}],
        bundle_id="eb_cu_hong",
    )
    store.add_evidence_bundle(
        work_item_id,
        **_bundle(items=[dict(_CONTRACT_ITEM)], gaps=[{"kind": "missing_evidence", "detail": "Chưa đủ."}]),
        bundle_id="eb_moi_tot",
    )
    # Ép thứ tự thời gian để "mới nhất" là xác định, không phụ thuộc hai bản ghi trùng dấu thời gian.
    with store.engine.begin() as connection:
        connection.execute(
            text("UPDATE evidence_bundles SET created_at = :when WHERE bundle_id = :bundle_id"),
            {"when": "2026-01-01 00:00:00+00:00", "bundle_id": "eb_cu_hong"},
        )
        connection.execute(
            text("UPDATE evidence_bundles SET created_at = :when WHERE bundle_id = :bundle_id"),
            {"when": "2026-01-02 00:00:00+00:00", "bundle_id": "eb_moi_tot"},
        )

    response = await client.get(f"/api/v2/work-items/{work_item_id}", headers=_headers("investigator"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert [bundle["bundle_id"] for bundle in body["evidence_bundles"]] == ["eb_moi_tot"]
    # Nói thẳng ra đã bỏ gì: một hồ sơ thiếu mà im lặng trông y hệt một hồ sơ đầy.
    assert [item["bundle_id"] for item in body["dropped_evidence_bundles"]] == ["eb_cu_hong"]
    assert "doc_id" in " ".join(body["dropped_evidence_bundles"][0]["violations"])

    # Đường đọc gói riêng vẫn trả gói mới nhất, không dính gì tới gói cũ hỏng.
    single = await client.get(
        f"/api/v2/work-items/{work_item_id}/evidence-bundle", headers=_headers("investigator")
    )
    assert single.status_code == 200, single.text
    assert single.json()["bundle_id"] == "eb_moi_tot"

    # Không có gì bị bỏ thì không được sinh khoá rỗng ra.
    clean = await _create(client)
    store.add_evidence_bundle(clean["work_item_id"], **_bundle(items=[dict(_CONTRACT_ITEM)], gaps=[]))
    envelope = await client.get(
        f"/api/v2/work-items/{clean['work_item_id']}", headers=_headers("investigator")
    )
    assert envelope.status_code == 200
    assert "dropped_evidence_bundles" not in envelope.json()


@pytest.mark.asyncio
async def test_a_broken_newest_bundle_still_stops_the_read(v2_client_with_store):
    """Gỡ gói cũ hỏng không được nới thành gỡ luôn gói mới nhất: gói mới nhất là câu trả lời.

    Giữ đúng tính đóng-an-toàn ở chỗ cần: không có gói mới nhất đọc được thì không có gì để trả lời,
    và trả 500 là đúng hơn trả một hồ sơ trông như đầy.
    """
    client, store = v2_client_with_store
    created = await _create(client)
    work_item_id = created["work_item_id"]
    store.add_evidence_bundle(
        work_item_id,
        **_bundle(items=[dict(_CONTRACT_ITEM)], gaps=[]),
        bundle_id="eb_cu_tot",
    )
    _seed_unchecked_bundle(
        store,
        work_item_id,
        items=[{"evidence_id": "EVI-2", "quote": "Gói mới nhất bị hỏng."}],
        gaps=[],
        bundle_id="eb_moi_hong",
    )
    with store.engine.begin() as connection:
        connection.execute(
            text("UPDATE evidence_bundles SET created_at = :when WHERE bundle_id = :bundle_id"),
            {"when": "2026-01-01 00:00:00+00:00", "bundle_id": "eb_cu_tot"},
        )
        connection.execute(
            text("UPDATE evidence_bundles SET created_at = :when WHERE bundle_id = :bundle_id"),
            {"when": "2026-01-02 00:00:00+00:00", "bundle_id": "eb_moi_hong"},
        )

    response = await client.get(f"/api/v2/work-items/{work_item_id}", headers=_headers("investigator"))
    assert response.status_code == 500, response.text
    body = response.json()
    assert body["error"]["code"] == "unavailable"
    assert body["error"]["details"]["bundle_id"] == "eb_moi_hong"


# ---------------------------------------------- hai lỗ của vòng kiểm thử thứ tư
@pytest.mark.asyncio
async def test_an_impossible_expected_version_is_a_conflict_not_a_crash(v2_client_with_store):
    """``expected_version`` vượt trần int4 phải là **409**, không phải 500 văn bản trần.

    Đo được trước khi sửa: ``PATCH`` với ``expected_version = 2147483647`` trả **500**
    ``text/plain`` "Internal Server Error" — ``_apply_work_item_change`` cộng ``expected + 1`` rồi
    gán vào cột ``version`` (int4) nên cơ sở dữ liệu ném ``NumericValueOutOfRange``. Lỗi đó do người
    gọi gây ra và trả lời được, nên phải là một thân lỗi hợp đồng. Đường duyệt phiếu trả lời đã so
    sánh trước từ lâu và trả 409 cho đúng giá trị này — hai đường phải nói cùng một câu.

    Giới hạn của bài này: **SQLite không có int4**, nên ở đây bài xanh cả khi thiếu chốt trần (nó
    vẫn 409 nhờ nhánh ``rowcount != 1``). Bài chỉ thật sự phân biệt trên PostgreSQL. Đã chứng minh
    đỏ ở đó: không có chốt trần thì ``PATCH`` trả **500** ``text/plain`` "Internal Server Error";
    có chốt trần thì **409** ``application/json`` với thân lỗi hợp đồng.
    """
    client, store = v2_client_with_store
    created = await client.post(
        "/api/v2/work-items",
        headers=_headers("investigator"),
        json={"question": "Câu hỏi?", "context": {"requester": {"id": "usr_investigator"}, "channel": "web", "raw_text": "x", "language": "vi"}},
    )
    assert created.status_code == 201, created.text
    work_item_id = created.json()["work_item_id"]

    response = await client.patch(
        f"/api/v2/work-items/{work_item_id}",
        headers=_headers("investigator"),
        json={"expected_version": 2**31 - 1, "priority": "urgent"},
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == ErrorCode.VERSION_CONFLICT.value
    assert body["error"]["details"]["expected_version"] == 2**31 - 1
    # Và bản ghi không được đổi: yêu cầu vẫn ở phiên bản cũ.
    reread = await client.get(f"/api/v2/work-items/{work_item_id}", headers=_headers("investigator"))
    assert reread.json()["work_item"]["version"] == 1


def test_a_bundle_entry_that_is_not_an_object_is_dropped_not_fatal():
    """Mục không phải đối tượng là **dữ liệu hỏng**, không phải lỗi máy chủ.

    Hàm này nằm trên đường 500 dùng chung, nên ``bundle.get`` ném ``AttributeError`` là cả ca đổ
    theo — đúng thứ mà nó sinh ra để chặn. Đo được trước khi sửa:
    ``AttributeError: 'NoneType' object has no attribute 'get'``.
    """
    from src.api.v2_routes import _split_older_bundles

    newest = {
        "bundle_id": "eb_moi",
        "work_item_id": "wi_1",
        "investigation_id": "INV-1",
        "created_at": "2026-01-02T00:00:00Z",
        "items": [],
        "gaps": [],
        "coverage": {
            "documents_retrieved": 0,
            "sources_ok": [],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": False,
        },
        "assessment_status": "insufficient_evidence",
        "source_errors": [],
    }
    kept, dropped = _split_older_bundles("wi_1", [None, "chuỗi", 7, [1, 2], newest])
    assert kept == [newest]
    assert len(dropped) == 4
    assert all(item["bundle_id"] is None for item in dropped)
    assert all(item["violations"] for item in dropped)
    assert all("không phải đối tượng" in item["violations"][0] for item in dropped)


def test_a_broken_newest_bundle_reports_itself_instead_of_crashing():
    """Mục **mới nhất** không phải đối tượng thì phải là lỗi hợp đồng, không phải ``AttributeError``.

    Vòng kiểm thử thứ năm tìm ra khe này: ``_split_older_bundles`` đã kiểm kiểu cho các mục cũ,
    nhưng ``_require_contract_shaped_bundles`` — chạy trên đúng mục mới nhất — vẫn gọi
    ``bundle.get("bundle_id")`` trong **chính nhánh báo lỗi**. Không kiểm thì nhánh đó ném
    ``AttributeError`` và người gọi nhận 500 văn bản trần: hàm sinh ra để chặn 500 lại tự tạo 500.
    """
    from src.api.v2_routes import _require_contract_shaped_bundles
    from src.services.errors import MvpError

    with pytest.raises(MvpError) as caught:
        _require_contract_shaped_bundles("wi_1", [None])
    assert caught.value.status == 500
    assert caught.value.code == ErrorCode.UNAVAILABLE
    assert caught.value.details["bundle_id"] is None
    assert caught.value.details["violations"], "phải nói rõ sai ở đâu"

    # Cùng câu trả lời cho các kiểu không phải đối tượng khác, và cho một mục là dict nhưng hỏng.
    for entry in ("chuỗi", 7, [1, 2], True):
        with pytest.raises(MvpError) as other:
            _require_contract_shaped_bundles("wi_1", [entry])
        assert other.value.details["bundle_id"] is None

    with pytest.raises(MvpError) as broken:
        _require_contract_shaped_bundles("wi_1", [{"bundle_id": "eb_hong"}])
    assert broken.value.details["bundle_id"] == "eb_hong"
