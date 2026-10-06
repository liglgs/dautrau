"""B1.2 — ma trận quyền rút gọn: mỗi vai × một tuyến đại diện cho mỗi nhóm quyền.

Toàn bộ đi qua điểm cuối HTTP thật (``ASGITransport``). Danh tính dựng bằng ``X-Test-User`` của
``TestProvider`` (chỉ bật khi ``VIGILENS_TEST_AUTH=1`` và ``APP_ENV != production``).

Quy ước mã trạng thái:
  * ``404 not_found`` — có xác thực nhưng ca nằm ngoài phạm vi (AUTH-02: không tiết lộ ca có tồn tại).
  * ``403 forbidden`` — thiếu hẳn quyền, không liên quan tới ca cụ thể.
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app
from src.models.schemas import CheckpointKind, ClaimInput, RunStatus

CLAIM = {
    "claim_text": "aspirin gây chảy máu tiêu hoá",
    "drug": "aspirin",
    "event": "chảy máu tiêu hoá",
}

ROLES = ("investigator", "reviewer", "admin", "service", "auditor")

OWNER = "usr_chu_ca"


def _headers(role: str) -> dict[str, str]:
    return {"X-Test-User": f"usr_{role}:{role}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def matrix_client(monkeypatch, tmp_path):
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "matrix.db"))
    async with _client() as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


def _seed_case(created_by: str = OWNER) -> str:
    """Ca đang chờ duyệt ở cổng đánh giá, ghim trạng thái để không đua với runner nền."""
    store = get_mvp_store()
    state, _ = store.create_investigation(ClaimInput(**CLAIM), created_by=created_by)
    store.save_state(
        state.model_copy(
            update={"run_status": RunStatus.WAITING_FOR_REVIEW, "checkpoint": CheckpointKind.ASSESSMENT}
        )
    )
    return state.investigation_id


def _current_version(case_id: str) -> int:
    return get_mvp_store().get_state(case_id).version


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ROLES)
async def test_create_investigation(matrix_client: AsyncClient, role: str):
    """``investigation:create``: I, R, A, S được tạo; kiểm toán chỉ đọc nên bị chặn."""
    response = await matrix_client.post(
        "/api/v1/investigations",
        json=CLAIM,
        headers={**_headers(role), "Idempotency-Key": f"tao-{role}"},
    )
    if role == "auditor":
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "forbidden"
    else:
        # 429 là điều kiện tài nguyên (runner bận), không phải câu trả lời về quyền.
        assert response.status_code in (202, 429), response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ROLES)
async def test_read_own_case(matrix_client: AsyncClient, role: str):
    """``investigation:read:*``: cả năm vai đọc được ca của chính mình."""
    case_id = _seed_case(created_by=f"usr_{role}")
    response = await matrix_client.get(f"/api/v1/investigations/{case_id}", headers=_headers(role))
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "expected"),
    [("investigator", 404), ("reviewer", 200), ("admin", 200), ("service", 200), ("auditor", 200)],
)
async def test_read_someone_elses_case(matrix_client: AsyncClient, role: str, expected: int):
    """``investigation:read:any``: chỉ I bị chặn, và bị chặn bằng 404 chứ không phải 403."""
    case_id = _seed_case()
    response = await matrix_client.get(f"/api/v1/investigations/{case_id}", headers=_headers(role))
    assert response.status_code == expected, response.text
    if expected == 404:
        assert response.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "expected"),
    [("investigator", 404), ("reviewer", 200), ("admin", 200), ("service", 200), ("auditor", 404)],
)
async def test_cancel_someone_elses_case(matrix_client: AsyncClient, role: str, expected: int):
    """``investigation:run:*``: I thiếu ``:any``; kiểm toán không có quyền chạy nào.

    Cả hai đều nhận 404 vì ``require_investigation_access`` cố ý trả 404 thay vì 403 để không
    tiết lộ ca có tồn tại hay không (AUTH-02).
    """
    case_id = _seed_case()
    response = await matrix_client.post(f"/api/v1/investigations/{case_id}/cancel", headers=_headers(role))
    assert response.status_code == expected, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "expected"),
    [("investigator", 403), ("reviewer", 200), ("admin", 403), ("service", 403), ("auditor", 403)],
)
async def test_decide_is_reviewer_only(matrix_client: AsyncClient, role: str, expected: int):
    """``review:decide``: chỉ người duyệt. Quản trị **không** quyết định chuyên môn (B1.5)."""
    case_id = _seed_case()
    response = await matrix_client.post(
        f"/api/v1/investigations/{case_id}/reviews",
        headers=_headers(role),
        json={
            "decision_id": f"qđ-{role}",
            "action": "reject",
            "checkpoint": "assessment",
            "expected_version": _current_version(case_id),
            "reason": "Bài kiểm thử ma trận quyền: lý do đủ dài để qua ngưỡng RV-04.",
        },
    )
    assert response.status_code == expected, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ROLES)
async def test_warehouse_read(matrix_client: AsyncClient, role: str):
    """``warehouse:read``: cả năm vai tra cứu được thuốc."""
    response = await matrix_client.get("/api/v1/drugs/lookup", params={"name": "aspirin"}, headers=_headers(role))
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "allowed"),
    [("investigator", False), ("reviewer", True), ("admin", True), ("service", True), ("auditor", False)],
)
async def test_warehouse_ingest(matrix_client: AsyncClient, role: str, allowed: bool):
    """``warehouse:ingest``: R, A, S được nạp; I và kiểm toán thì không."""
    response = await matrix_client.post(
        "/api/v1/ingestion/documents",
        headers=_headers(role),
        json={
            "source": "pubmed",
            "source_id": f"kiem-thu-{role}",
            "title": "Tài liệu kiểm thử ma trận quyền",
            "text": "Nội dung kiểm thử.",
        },
    )
    if allowed:
        # Kho ELT có thể chưa dựng trong môi trường ngoại tuyến; điều cần khẳng định là **không**
        # bị chặn vì quyền.
        assert response.status_code not in (401, 403), response.text
    else:
        assert response.status_code == 403, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "scope"),
    [("investigator", "own"), ("reviewer", "own"), ("admin", "any"), ("service", "own"), ("auditor", "any")],
)
async def test_audit_scope(matrix_client: AsyncClient, role: str, scope: str):
    """``audit:read:own`` cho bốn vai; ``audit:read:any`` chỉ quản trị và kiểm toán."""
    response = await matrix_client.get("/api/v1/admin/audit", headers=_headers(role))
    assert response.status_code == 200, response.text
    assert response.json()["scope"] == scope


@pytest.mark.asyncio
async def test_audit_own_scope_hides_other_peoples_events(matrix_client: AsyncClient):
    """Phạm vi ``own`` thật sự lọc: người điều tra không thấy ca của người khác trong nhật ký."""
    case_id = _seed_case()
    store = get_mvp_store()
    store.audit(case_id, "usr_chu_ca", "tao_ca", actor_role="investigator")
    own = await matrix_client.get("/api/v1/admin/audit", headers=_headers("investigator"))
    assert own.json()["items"] == []
    other = await matrix_client.get("/api/v1/admin/audit", headers=_headers("auditor"))
    actors = {item["actor"] for item in other.json()["items"]}
    assert "usr_chu_ca" in actors


@pytest.mark.asyncio
async def test_audit_jsonl_export_carries_the_actor_id(matrix_client: AsyncClient):
    """AUTH-03: bản kết xuất JSONL ghi mã người, không ghi chuỗi vai."""
    case_id = _seed_case()
    store = get_mvp_store()
    store.audit(case_id, "usr_nguoi_duyet_that", "duyet_ho_so", actor_role="reviewer")
    response = await matrix_client.get(
        "/api/v1/admin/audit", params={"format": "jsonl"}, headers=_headers("admin")
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    lines = [line for line in response.text.splitlines() if line.strip()]
    import json

    rows = [json.loads(line) for line in lines]
    duyet = [row for row in rows if row["action"] == "duyet_ho_so"]
    assert len(duyet) == 1
    row: dict[str, Any] = duyet[0]
    assert row["actor"] == "usr_nguoi_duyet_that"
    assert row["actor_role"] == "reviewer"
    assert row["legacy_actor"] is False
