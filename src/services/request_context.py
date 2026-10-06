"""Mã yêu cầu dùng chung cho cả envelope lỗi lẫn nhật ký kiểm toán.

Vì sao cần: `audit_events.request_id` chỉ có ích khi nó **trùng** với `request_id` mà người dùng
nhìn thấy trong phản hồi lỗi — có vậy mới tra ngược được "lỗi này là do thao tác nào". Trước đây
mã được sinh riêng trong `_error_envelope`, chỉ dành cho phản hồi lỗi, nên mọi dòng nhật ký đều
có `request_id = NULL`.

Cách làm: middleware sinh một mã cho mỗi yêu cầu và đặt vào `ContextVar`. Tầng lưu trữ đọc lại
biến đó khi không được truyền mã tường minh, nên mọi điểm ghi nhật ký đều có mã mà không phải
sửa từng lời gọi. Việc chạy nền không có yêu cầu nào ⇒ giá trị là `None`, đúng như mong đợi.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("vigilens_request_id", default=None)


def set_request_id(value: str) -> Token[str | None]:
    """Đặt mã cho yêu cầu đang xử lý; trả token để khôi phục ở ``finally``."""
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def current_request_id() -> str | None:
    return _request_id.get()
