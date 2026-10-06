"""Kiểm thử cookie phiên, đăng nhập thật và phân quyền theo chủ ca (Người 2).

AUTH-01: đăng nhập phải kiểm credential — không còn nhánh "tự khai vai", ``session_id`` không
nằm trong thân phản hồi, cookie là HttpOnly.
AUTH-02: đọc/ghi chéo ca trả **404** (không phải 403) để không tiết lộ ca có tồn tại hay không.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.auth import SESSION_COOKIE_NAME, hash_password
from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app

CLAIM = {
    "claim_text": "aspirin causes gastrointestinal bleeding",
    "drug": "aspirin",
    "event": "gastrointestinal bleeding",
}

PASSWORD = "mat-khau-kiem-thu-01"

USERS = (
    ("usr_alice", "alice@benhvien.test", "investigator", "Alice"),
    ("usr_bob", "bob@benhvien.test", "investigator", "Bob"),
    ("usr_reviewer", "reviewer@benhvien.test", "reviewer", "Bác sĩ duyệt"),
)


def _new_client() -> AsyncClient:
    """Client riêng cho mỗi người: cookie phiên không rò từ người này sang người khác."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def auth_client(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "test-inv-token")
    monkeypatch.setenv("REVIEWER_TOKEN", "test-rev-token")
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "auth_test.db"))
    store = get_mvp_store()
    for user_id, email, role, display_name in USERS:
        store.create_user(
            user_id=user_id,
            email=email,
            role=role,
            display_name=display_name,
            password_hash=hash_password(PASSWORD),
        )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


async def _login(client: AsyncClient, email: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_auth_login_sets_cookie_and_me_reads_it(auth_client: AsyncClient):
    """Đăng nhập bằng email + mật khẩu, nhận cookie phiên HttpOnly và gọi /me."""
    res = await auth_client.post(
        "/api/v1/auth/login", json={"email": "alice@benhvien.test", "password": PASSWORD}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "investigator"
    assert data["user_id"] == "usr_alice"
    # AUTH-01: mã phiên chỉ đi trong cookie HttpOnly, không trả về thân phản hồi.
    assert "session_id" not in data
    assert SESSION_COOKIE_NAME in res.cookies
    assert res.cookies[SESSION_COOKIE_NAME]

    # 2. Gọi /me dùng session cookie đã lưu trong client
    res_me = await auth_client.get("/api/v1/auth/me")
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["user_id"] == "usr_alice"
    assert me_data["role"] == "investigator"
    assert me_data["auth_method"] == "local_session"

    # 3. Đăng xuất
    res_logout = await auth_client.post("/api/v1/auth/logout")
    assert res_logout.status_code == 200
    assert res_logout.json()["logged_out"] is True

    # 4. Gọi lại /me sau khi logout -> 401
    res_me_after = await auth_client.get("/api/v1/auth/me")
    assert res_me_after.status_code == 401


@pytest.mark.asyncio
async def test_login_requires_a_real_credential(auth_client: AsyncClient):
    """AUTH-01: tự khai vai, sai mật khẩu, hoặc tài khoản lạ đều không được cấp phiên."""
    for body in (
        {"role": "reviewer"},
        {"token": "test-rev-token", "username": "ke-gia-danh"},
        {"email": "alice@benhvien.test", "password": "sai-mat-khau", "role": "reviewer"},
    ):
        response = await auth_client.post("/api/v1/auth/login", json=body)
        assert response.status_code in (401, 422), (body, response.text)
        assert SESSION_COOKIE_NAME not in response.cookies

    unknown = await auth_client.post(
        "/api/v1/auth/login", json={"email": "khong-ton-tai@benhvien.test", "password": PASSWORD}
    )
    assert unknown.status_code == 401
    assert unknown.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_ownership_enforcement_on_cancel(auth_client: AsyncClient):
    """Người khác vai điều tra không hủy được ca của Alice; người duyệt thì hủy được."""
    from src.models.schemas import ClaimInput, RunStatus

    store = get_mvp_store()
    async with _new_client() as alice_client:
        await _login(alice_client, "alice@benhvien.test")
        # Alice thật sự đăng nhập được bằng phiên của mình.
        assert (await alice_client.get("/api/v1/auth/me")).json()["user_id"] == "usr_alice"

    # Ca được tạo thẳng trong kho rồi ghim ở trạng thái chờ: bài này kiểm phân quyền, không kiểm
    # lượt chạy nền — để runner tự chạy thì nó có thể hoàn tất trước và hủy sẽ hỏng vì lý do khác.
    state, _ = store.create_investigation(ClaimInput(**CLAIM), created_by="usr_alice")
    inv_id = state.investigation_id
    store.save_state(state.model_copy(update={"run_status": RunStatus.WAITING_FOR_REVIEW}))

    async with _new_client() as bob_client:
        await _login(bob_client, "bob@benhvien.test")
        # AUTH-02: Bob chỉ có ``investigation:run:own`` ⇒ 404, và thông báo không xác nhận
        # rằng ca này có tồn tại.
        cancel_res = await bob_client.post(f"/api/v1/investigations/{inv_id}/cancel")
        assert cancel_res.status_code == 404
        assert cancel_res.json()["error"]["code"] == "not_found"

    async with _new_client() as rev_client:
        await _login(rev_client, "reviewer@benhvien.test")
        cancel_res = await rev_client.post(f"/api/v1/investigations/{inv_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["cancelled"] is True
        assert cancel_res.json()["run_status"] == "cancelled"


@pytest.mark.asyncio
async def test_backward_compatibility_with_headers(auth_client: AsyncClient):
    """Khoá tĩnh cũ vẫn chạy được ngoài production, nhưng được ghi rõ là khoá tạm."""
    res = await auth_client.get("/api/v1/investigations", headers={"X-API-Token": "test-inv-token"})
    assert res.status_code == 200

    res_bearer = await auth_client.get(
        "/api/v1/investigations", headers={"Authorization": "Bearer test-rev-token"}
    )
    assert res_bearer.status_code == 200

    me = await auth_client.get("/api/v1/auth/me", headers={"X-API-Token": "test-inv-token"})
    assert me.status_code == 200
    assert me.json()["auth_method"] == "legacy_token"
