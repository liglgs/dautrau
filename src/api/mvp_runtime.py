"""Singleton runtime cho API MVP: một store SQLite + một runner trong tiến trình (M02/M07).

Đặt ở module riêng để ``src/api/investigations.py`` chỉ phụ thuộc một hàm lấy store,
và để test có thể cấu hình lại bằng ``configure_mvp`` / ``reset_mvp``.
"""

from __future__ import annotations

import logging
from threading import RLock

from src.config import get_settings
from src.services.runmode import describe_run_mode, validate_run_mode
from src.services.runner import InProcessRunner, configure_runner, get_runner
from src.services.store import MvpStore

logger = logging.getLogger(__name__)

_store: MvpStore | None = None
#: Khoá khởi tạo lười: hai request đầu tiên cùng lúc không được tạo hai store/runner.
_lock = RLock()


def configure_mvp(db_path: str | None = None, *, force: bool = False) -> MvpStore:
    """Khởi tạo store + runner (gọi trong lifespan hoặc trong test).

    Idempotent theo mặc định: nếu store đã tồn tại thì trả lại store đó, tránh tạo thêm kết nối
    SQLite khi nhiều request cùng khởi động. ``force=True`` dùng cho test cần đổi DB.

    RT-01: tổ hợp chế độ sai bị chặn **ở đây**, tức là lúc dựng app, chứ không đợi tới request đầu
    tiên. Nhờ vậy không có cửa sổ nào để một lượt chạy ra kết quả nửa thật nửa mẫu.
    """
    global _store
    with _lock:
        if _store is not None and not force:
            return _store
        settings = get_settings()
        validate_run_mode(settings)
        logger.info(describe_run_mode(settings))
        executor, gateway = None, None
        if settings.mvp_evidence_mode == "person3_demo":
            from src.services.evidence.demo import make_demo_runtime

            executor, gateway = make_demo_runtime(settings.mvp_person3_demo_scenario)
        elif settings.mvp_evidence_mode == "person3":
            from src.services.evidence.integration import make_person3_executor

            executor = make_person3_executor(settings.mvp_dictionary_path)
        previous, _store = _store, MvpStore(db_path or settings.mvp_db_path)
        configure_runner(_store, executor=executor, gateway=gateway)
    if previous is not None and previous is not _store:
        previous.close()
    return _store


def get_mvp_store() -> MvpStore:
    """Store của app; khởi tạo lười nếu lifespan chưa chạy (ASGI test, app được mount)."""
    global _store
    if _store is not None:
        return _store
    with _lock:  # kiểm tra lại trong khoá: hai request đầu tiên không tạo hai store
        if _store is None:
            _store = configure_mvp(force=True)
        return _store


def get_mvp_runner() -> InProcessRunner:
    return get_runner()


def reset_mvp() -> None:
    """Xoá singleton (dùng trong test) và đóng kết nối SQLite của store cũ."""
    global _store
    with _lock:
        previous, _store = _store, None
    if previous is not None:
        previous.close()
