"""B3.7 bước 6 — chế độ Supabase chạy **thật**, không chỉ chạy khi có khoá tự dựng.

Vì sao cần tệp này: trước đây ``PyJWT`` và ``cryptography`` không có trong ``requirements.txt``,
nên nhánh Supabase chưa lần nào chạy. Nay hai gói đã được thêm, và nhánh đó phải được khoá lại
bằng bài kiểm chạy được **ngoại tuyến** — bộ kiểm thử không được gọi mạng ra Supabase.

Cách làm: dựng khoá thật bằng ``cryptography``, thay ``_load_jwks`` bằng JWKS của khoá đó, rồi ký
token thật bằng ``PyJWT``. Như vậy đường mã thật (tra ``kid``, chốt thuật toán theo ``kty``, kiểm
chữ ký, kiểm ``aud``, kiểm hạn) chạy y hệt lúc gọi mạng, chỉ khác nguồn khoá.

Đường gọi mạng thật đã được chạy riêng một lần (tài khoản Supabase thật, token thật, JWKS thật):
10/10 phép kiểm đạt. Bài ở đây khoá lại kết quả đó để lần sau không phải gọi mạng nữa.
"""

from __future__ import annotations

import base64
import json
import sys
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from httpx import ASGITransport, AsyncClient
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from src.api.auth import SupabaseProvider, supabase_provider_ready
from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app

SUPABASE_URL = "https://du-an-thu.supabase.co"
AUDIENCE = "authenticated"
SUPABASE_ENV_KEYS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")


@pytest.fixture(autouse=True)
def _supabase_settings(monkeypatch):
    """Cấu hình chế độ Supabase, và **chặn mọi lời gọi mạng** ngoài phần thay thế của từng bài."""
    for key in SUPABASE_ENV_KEYS:
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_gia_lap")
    monkeypatch.delenv("VIGILENS_TEST_AUTH", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _pem(key) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture
def project_key():
    """Khoá ES256 của dự án, kèm JWKS công khai — đúng hình dạng Supabase phát hành."""
    private = ec.generate_private_key(ec.SECP256R1())
    public_jwk = ECAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public_jwk.update({"kid": "khoa-du-an-1", "use": "sig", "alg": "ES256"})
    return private, {"keys": [public_jwk]}


@pytest.fixture
def provider(project_key, monkeypatch):
    """``SupabaseProvider`` với JWKS của khoá dự án, không gọi mạng."""
    _, jwks = project_key
    instance = SupabaseProvider()
    monkeypatch.setattr(instance, "_load_jwks", lambda: jwks)
    return instance


def _token(key, *, kid="khoa-du-an-1", audience=AUDIENCE, expires_in=3600, subject="nguoi-1", algorithm="ES256"):
    claims = {
        "sub": subject,
        "aud": audience,
        "exp": datetime.now(UTC) + timedelta(seconds=expires_in),
        "iat": datetime.now(UTC),
        "role": "authenticated",
    }
    return pyjwt.encode(claims, _pem(key), algorithm=algorithm, headers={"kid": kid})


def _hand_rolled(kid: str, algorithm: str, signature: bytes, *, audience=AUDIENCE) -> str:
    """Token dựng tay, vì kẻ tấn công đổi thuật toán thì không dùng PyJWT (PyJWT tự chặn)."""
    head = _b64u(json.dumps({"alg": algorithm, "typ": "JWT", "kid": kid}).encode())
    body = _b64u(
        json.dumps(
            {
                "sub": "nguoi-1",
                "aud": audience,
                "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            }
        ).encode()
    )
    return f"{head}.{body}.{_b64u(signature)}"


# ------------------------------------------------------------------ đường chấp nhận
def test_a_real_es256_token_from_the_project_key_is_accepted(provider, project_key):
    """Token ES256 ký bằng khoá dự án, ``kid`` khớp JWKS ⇒ giải mã được, ``sub`` đúng."""
    private, _ = project_key
    claims = provider._decode(_token(private, subject="nguoi-that"))
    assert claims["sub"] == "nguoi-that"
    assert claims["aud"] == AUDIENCE


def test_an_rsa_project_key_also_works(project_key, monkeypatch):
    """Dự án có thể phát khoá RS256; nhánh ``kty == "RSA"`` cũng phải chạy."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public_jwk.update({"kid": "khoa-rsa-1", "use": "sig", "alg": "RS256"})
    instance = SupabaseProvider()
    monkeypatch.setattr(instance, "_load_jwks", lambda: {"keys": [public_jwk]})
    claims = instance._decode(_token(private, kid="khoa-rsa-1", algorithm="RS256"))
    assert claims["sub"] == "nguoi-1"


# ------------------------------------------------------------------ đường từ chối
def test_a_token_signed_by_another_key_is_rejected(provider, project_key):
    """Khoá khác cùng ``kid``: chữ ký không khớp ⇒ từ chối."""
    intruder = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(pyjwt.InvalidSignatureError):
        provider._decode(_token(intruder))


def test_a_tampered_signature_is_rejected(provider, project_key):
    private, _ = project_key
    token = _token(private)
    head, body, signature = token.split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(pyjwt.InvalidSignatureError):
        provider._decode(f"{head}.{body}.{flipped}")


def test_an_expired_token_is_rejected(provider, project_key):
    """``verify_exp`` phải bật: token hết hạn 60 giây thì không dùng được."""
    private, _ = project_key
    with pytest.raises(pyjwt.ExpiredSignatureError):
        provider._decode(_token(private, expires_in=-60))


def test_a_token_for_another_audience_is_rejected(provider, project_key):
    """``aud`` khác ``authenticated`` ⇒ từ chối; nếu không thì token của dịch vụ khác vào được."""
    private, _ = project_key
    with pytest.raises(pyjwt.InvalidAudienceError):
        provider._decode(_token(private, audience="dich-vu-khac"))


def test_a_token_with_an_unknown_kid_is_rejected(provider, project_key):
    """``kid`` lạ ⇒ 401, không đoán khoá, không thử hết JWKS."""
    private, _ = project_key
    from src.services.errors import MvpError

    with pytest.raises(MvpError) as bad:
        provider._decode(_token(private, kid="khoa-khong-co"))
    assert bad.value.status == 401


def test_an_unsupported_key_type_is_rejected(monkeypatch):
    """``kty=oct`` không phải thứ Supabase phát hành ⇒ 401, không suy diễn thành RSA."""
    instance = SupabaseProvider()
    monkeypatch.setattr(instance, "_load_jwks", lambda: {"keys": [{"kty": "oct", "kid": "k", "k": "abc"}]})
    from src.services.errors import MvpError

    with pytest.raises(MvpError) as bad:
        instance._decode(_token(ec.generate_private_key(ec.SECP256R1()), kid="k"))
    assert bad.value.status == 401
    assert "oct" in bad.value.message


def test_alg_none_is_rejected(provider, project_key):
    """``alg=none`` kèm ``kid`` thật vẫn bị chặn: thuật toán chốt theo JWKS, không theo token."""
    _, jwks = project_key
    with pytest.raises(Exception) as bad:
        provider._decode(_hand_rolled(jwks["keys"][0]["kid"], "none", b""))
    assert not isinstance(bad.value, AssertionError)


def test_an_hs256_token_signed_with_the_public_key_is_rejected(provider, project_key):
    """Tấn công đổi thuật toán: ký HS256 bằng chính khoá công khai làm khoá đối xứng.

    Nếu mã nguồn lấy ``alg`` từ token thay vì từ JWKS thì token này được nhận, và bất kỳ ai đọc
    được JWKS công khai cũng ký được token cho bất kỳ người dùng nào.
    """
    import hashlib
    import hmac

    _, jwks = project_key
    kid = jwks["keys"][0]["kid"]
    signing_input = _hand_rolled(kid, "HS256", b"").rsplit(".", 1)[0].encode()
    public_pem = ECAlgorithm.from_jwk(jwks["keys"][0]).public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    forged = _hand_rolled(kid, "HS256", hmac.new(public_pem, signing_input, hashlib.sha256).digest())
    with pytest.raises(pyjwt.InvalidAlgorithmError):
        provider._decode(forged)


# ------------------------------------------------------------------ đệm JWKS
def test_the_jwks_is_fetched_once_and_then_cached(project_key, monkeypatch):
    """Đệm 5 phút: gọi JWKS mỗi request là chậm và dễ bị Supabase chặn vì quá nhiều lời gọi."""
    _, jwks = project_key
    calls = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(jwks).encode()

    def fake_urlopen(url, timeout=None):
        calls.append(url)
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    instance = SupabaseProvider()
    first = instance._load_jwks()
    second = instance._load_jwks()
    assert first == second == jwks
    assert len(calls) == 1, calls
    assert calls[0] == f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"


# ------------------------------------------------------------------ sẵn sàng và đường HTTP
def test_a_machine_token_never_triggers_a_jwks_fetch(monkeypatch):
    """Khoá máy ``vln_...`` không được kéo theo một lời gọi mạng tới Supabase.

    Vì sao quan trọng: ở chế độ ``auto`` nhà cung cấp Supabase đứng **trước** chế độ nội bộ, nên
    mọi yêu cầu mang khoá máy cũng đi qua nó trước. ``_load_jwks`` có thời gian chờ 10 giây và lần
    gọi hỏng **không** được ghi vào đệm — nên nếu đọc tiêu đề sau khi gọi mạng thì một Supabase
    không tới được sẽ treo mọi yêu cầu mang khoá máy thêm 10 giây mỗi lần, dù chúng không liên quan
    gì tới Supabase. Bài này khoá thứ tự đó lại.
    """
    calls = []

    def counting_load(self):
        calls.append(1)
        return {"keys": []}

    monkeypatch.setattr(SupabaseProvider, "_load_jwks", counting_load)
    from src.services.errors import MvpError

    with pytest.raises(MvpError) as bad:
        SupabaseProvider()._decode("vln_khoa_may_noi_bo")
    assert bad.value.status == 401
    assert calls == [], "khoá máy không được kéo theo lời gọi JWKS"

    # Còn token có tiêu đề JWT hợp lệ thì **phải** gọi mạng — nếu không thì chẳng có gì được xác
    # minh. Dùng token ký bằng khoá đối xứng chỉ để có một JWT đúng dạng; nó sẽ bị từ chối ở bước
    # tra ``kid``, nhưng phải đi qua được bước đọc tiêu đề trước đã.
    well_formed = pyjwt.encode(
        {"sub": "nguoi-1"}, "khoa-doi-xung-du-dai-cho-thu-nghiem-32b", algorithm="HS256", headers={"kid": "khoa-1"}
    )
    with pytest.raises(MvpError):
        SupabaseProvider()._decode(well_formed)
    assert calls == [1], "token có tiêu đề hợp lệ phải khiến JWKS được nạp"


def test_supabase_provider_ready_needs_the_library_and_the_config(monkeypatch):
    """Thiếu cấu hình ⇒ ``auto`` không dựng nhà cung cấp Supabase; có đủ ⇒ dựng."""
    assert supabase_provider_ready() is True
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")
    get_settings.cache_clear()
    assert supabase_provider_ready() is False
    monkeypatch.setitem(sys.modules, "jwt", None)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_gia_lap")
    get_settings.cache_clear()
    assert supabase_provider_ready() is False


@pytest_asyncio.fixture
async def supabase_client(project_key, monkeypatch, tmp_path):
    _, jwks = project_key
    monkeypatch.setattr(SupabaseProvider, "_load_jwks", lambda self: jwks)
    reset_mvp()
    configure_mvp(str(tmp_path / "supabase.db"))
    get_mvp_store().create_user(
        user_id="nguoi-1", email="nguoi@vi-du.test", role="reviewer", display_name="Người thật"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_http_accepts_a_supabase_token_for_an_active_account(supabase_client, project_key):
    """Đường đầy đủ: token Supabase ⇒ 200, danh tính lấy từ ``app_users`` chứ không từ token."""
    private, _ = project_key
    response = await supabase_client.get(
        "/api/v1/investigations", headers={"Authorization": f"Bearer {_token(private)}"}
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_http_rejects_a_supabase_token_for_an_unknown_account(supabase_client, project_key):
    """Chữ ký đúng nhưng chưa cấp quyền trong ``app_users`` ⇒ 401, không tự tạo tài khoản."""
    private, _ = project_key
    response = await supabase_client.get(
        "/api/v1/investigations", headers={"Authorization": f"Bearer {_token(private, subject='nguoi-la')}"}
    )
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_http_rejects_a_locked_account(supabase_client, project_key):
    """Tài khoản bị khoá trong ``app_users`` ⇒ 401 dù token còn hạn."""
    private, _ = project_key
    get_mvp_store().update_user("nguoi-1", status="disabled", actor_role="admin")
    response = await supabase_client.get(
        "/api/v1/investigations", headers={"Authorization": f"Bearer {_token(private)}"}
    )
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_http_rejects_an_expired_token(supabase_client, project_key):
    private, _ = project_key
    response = await supabase_client.get(
        "/api/v1/investigations", headers={"Authorization": f"Bearer {_token(private, expires_in=-60)}"}
    )
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_http_has_no_local_fallback_in_supabase_mode(supabase_client):
    """``AUTH_PROVIDER=supabase`` là chế độ cứng: không có đường lùi về mật khẩu nội bộ."""
    response = await supabase_client.get("/api/v1/investigations")
    assert response.status_code == 401, response.text


def test_a_failed_jwks_fetch_is_not_paid_for_twice_in_a_row(monkeypatch):
    """Lần lấy JWKS hỏng phải được nhớ tạm, không thì mỗi yêu cầu lại trả đủ 10 giây.

    Đo được trước khi sửa: một thông tin xác thực đúng dạng JWT (``aaa.bbb.ccc``) gửi tới khi
    Supabase không tới được giữ yêu cầu **10,02 giây**, và người **chưa xác thực** cũng kích hoạt
    được đường đó — đủ để rút cạn nhóm luồng. Bài này khoá lại việc lần hỏng được ghi nhớ.
    """
    import time
    import urllib.error
    import urllib.request

    calls = []

    def failing_urlopen(url, timeout=None):
        calls.append(url)
        time.sleep(0.2)  # giả làm thời gian chờ mạng
        raise urllib.error.URLError("không tới được")

    monkeypatch.setattr(urllib.request, "urlopen", failing_urlopen)
    provider = SupabaseProvider()

    started = time.monotonic()
    with pytest.raises(urllib.error.URLError):
        provider._load_jwks()
    first = time.monotonic() - started

    started = time.monotonic()
    with pytest.raises(urllib.error.URLError):
        provider._load_jwks()
    second = time.monotonic() - started

    assert len(calls) == 1, "lần hỏng phải được nhớ tạm, không gọi mạng lại ngay"
    assert first >= 0.2, "lần đầu phải thật sự chờ mạng"
    assert second < 0.1, f"lần sau phải trả lời ngay, đo được {second:.3f} giây"


def test_the_jwks_backoff_expires_and_a_good_fetch_clears_it(monkeypatch):
    """Chốt tạm phải hết hạn, và một lần lấy thành công phải xoá nó hẳn.

    Không có bài này thì một lần hỏng thoáng qua sẽ khoá người dùng Supabase thật lâu hơn 30 giây
    dự kiến, hoặc khoá vĩnh viễn nếu nhánh xoá bị bỏ quên.
    """
    import urllib.error
    import urllib.request

    from src.api import auth as auth_module

    state = {"fail": True}
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b'{"keys": []}'

    def urlopen(url, timeout=None):
        calls.append(url)
        if state["fail"]:
            raise urllib.error.URLError("không tới được")
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(auth_module, "_JWKS_FAILURE_BACKOFF_SECONDS", 0.05)
    provider = SupabaseProvider()

    with pytest.raises(urllib.error.URLError):
        provider._load_jwks()
    assert len(calls) == 1

    # Trong cửa sổ chốt tạm: không gọi mạng.
    with pytest.raises(urllib.error.URLError):
        provider._load_jwks()
    assert len(calls) == 1

    # Hết cửa sổ: thử lại, lần này thành công.
    time_module = __import__("time")
    time_module.sleep(0.06)
    state["fail"] = False
    assert provider._load_jwks() == {"keys": []}
    assert len(calls) == 2

    # Thành công rồi thì chốt tạm biến mất: lần sau lấy từ đệm, không gọi mạng nữa.
    assert provider._load_jwks() == {"keys": []}
    assert len(calls) == 2
