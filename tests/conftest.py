import ipaddress
import os
import socket
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

#: Biến môi trường ghim chế độ danh tính cho **mọi** bài kiểm thử (B1.6).
#: ``auth_provider=auto`` chọn Supabase khi thấy ``SUPABASE_URL``, mà ``.env`` của máy phát triển
#: có sẵn khoá đó — không ghim thì kết quả kiểm thử phụ thuộc ``.env`` từng máy và bài kiểm thử
#: sẽ gọi mạng. Chế độ ``local`` là mặc định khi chạy pytest theo đúng thiết kế B1.6.
#: ``SUPABASE_URL`` ghim rỗng (chứ không chỉ xoá khỏi ``os.environ``) vì pydantic-settings đọc
#: thẳng tệp ``.env``: xoá biến môi trường là chưa đủ để chặn giá trị trong tệp.
TEST_AUTH_ENV = {
    "AUTH_PROVIDER": "local",
    "APP_ENV": "test",
    "VIGILENS_TEST_AUTH": "1",
    "SUPABASE_URL": "",
    #: Khoá tĩnh cũ mặc định **tắt** (B1.7); bộ kiểm thử bật tường minh để vẫn phủ được nhánh đó.
    "VIGILENS_ALLOW_LEGACY_TOKENS": "1",
}
#: Khoá Supabase bị bỏ khỏi môi trường kiểm thử để không nhà cung cấp nào chạm tới mạng.
SUPABASE_ENV_KEYS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")


def _loopback_address(host):
    if isinstance(host, bytes):
        host = host.decode("ascii")
    if str(host).lower().rstrip(".") == "localhost":
        return True
    try:
        return ipaddress.ip_address(str(host)).is_loopback
    except ValueError:
        return False


def pytest_configure(config):
    """Block external network before test collection; allow local test servers."""
    for key, value in TEST_AUTH_ENV.items():
        os.environ[key] = value
    for key in SUPABASE_ENV_KEYS:
        os.environ.pop(key, None)

    guard = pytest.MonkeyPatch()
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex
    getaddrinfo = socket.getaddrinfo

    def check_address(address):
        if isinstance(address, tuple) and not _loopback_address(address[0]):
            raise RuntimeError("External network disabled in pytest; mock the request instead.")

    def guarded_connect(sock, address):
        check_address(address)
        return connect(sock, address)

    def guarded_connect_ex(sock, address):
        check_address(address)
        return connect_ex(sock, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host is not None and not _loopback_address(host):
            raise RuntimeError("External DNS disabled in pytest; mock the request instead.")
        return getaddrinfo(host, *args, **kwargs)

    guard.setattr(socket.socket, "connect", guarded_connect)
    guard.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    guard.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    config._p066_offline_network_guard = guard


def pytest_collection_modifyitems(config, items):
    """Bỏ qua các bài cần chromadb khi máy chưa cài ``requirements-elt.txt``.

    Giữ cho bộ kiểm thử chạy được trên máy chỉ cài ``requirements.lock.txt`` (CI và máy
    mới); khi có chromadb thì mọi bài vẫn chạy bình thường.
    """
    import importlib.util

    if importlib.util.find_spec("chromadb") is not None:
        return
    skip = pytest.mark.skip(reason="Chưa cài chromadb (xem requirements-elt.txt).")
    for item in items:
        if "needs_chroma" in item.keywords:
            item.add_marker(skip)


def pytest_unconfigure(config):
    guard = getattr(config, "_p066_offline_network_guard", None)
    if guard is not None:
        guard.undo()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
