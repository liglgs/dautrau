"""Lỗi nghiệp vụ MVP với envelope chuẩn ``{"error": {code, message, details, request_id}}``."""

from __future__ import annotations

from typing import Any

from src.models.schemas import ErrorCode


class MvpError(Exception):
    """Lỗi có mã, ánh xạ trực tiếp sang HTTP status và envelope lỗi của MVP."""

    def __init__(
        self,
        status: int,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)

    def envelope(self, request_id: str) -> dict[str, Any]:
        return {
            "error": {
                "code": str(self.code),
                "message": self.message,
                "details": self.details,
                "request_id": request_id,
                "retryable": self.retryable,
            }
        }


def invalid_request(message: str, details: dict[str, Any] | None = None) -> MvpError:
    return MvpError(422, ErrorCode.INVALID_REQUEST, message, details)


def unauthorized(message: str = "Thiếu hoặc sai token.") -> MvpError:
    return MvpError(401, ErrorCode.UNAUTHORIZED, message)


def forbidden(message: str = "Token không có quyền cho hành động này.") -> MvpError:
    return MvpError(403, ErrorCode.FORBIDDEN, message)


def not_found(what: str, identifier: str) -> MvpError:
    return MvpError(404, ErrorCode.NOT_FOUND, f"Không tìm thấy {what}: {identifier}", {"id": identifier})


def version_conflict(expected: int, current: int) -> MvpError:
    return MvpError(
        409,
        ErrorCode.VERSION_CONFLICT,
        f"Phiên bản đã cũ: expected_version={expected}, hiện tại={current}.",
        {"expected_version": expected, "current_version": current},
    )


def idempotency_conflict(key: str) -> MvpError:
    return MvpError(409, ErrorCode.IDEMPOTENCY_CONFLICT, "Idempotency-Key đã dùng với payload khác.", {"key": key})


def runner_busy(current: str | None) -> MvpError:
    return MvpError(
        429,
        ErrorCode.RUNNER_BUSY,
        "Đang có một cuộc điều tra khác chạy; mỗi thời điểm chỉ xử lý một cuộc.",
        {"current_investigation_id": current},
        retryable=True,
    )


def invalid_state(message: str, details: dict[str, Any] | None = None) -> MvpError:
    return MvpError(409, ErrorCode.INVALID_STATE, message, details)


def budget_exhausted(message: str, details: dict[str, Any] | None = None) -> MvpError:
    return MvpError(409, ErrorCode.BUDGET_EXHAUSTED, message, details)


def dossier_not_approved(investigation_id: str) -> MvpError:
    return MvpError(
        409,
        ErrorCode.DOSSIER_NOT_APPROVED,
        "Hồ sơ chưa được reviewer duyệt nên không thể export.",
        {"investigation_id": investigation_id},
    )


def dossier_invalid(investigation_id: str, errors: list[str]) -> MvpError:
    return MvpError(
        409,
        ErrorCode.DOSSIER_INVALID,
        "Hồ sơ không vượt qua kiểm tra an toàn nên không thể duyệt hoặc export.",
        {"investigation_id": investigation_id, "errors": errors},
    )


def source_error(message: str, details: dict[str, Any] | None = None) -> MvpError:
    return MvpError(502, ErrorCode.SOURCE_ERROR, message, details, retryable=True)


def llm_format_error(message: str, details: dict[str, Any] | None = None) -> MvpError:
    return MvpError(502, ErrorCode.LLM_FORMAT_ERROR, message, details)


def model_unavailable(message: str = "Mô hình AI không khả dụng.") -> MvpError:
    return MvpError(503, ErrorCode.MODEL_UNAVAILABLE, message, retryable=True)


def validation_details(exc: Exception) -> list[dict[str, Any]]:
    """Chi tiết lỗi pydantic ở dạng JSON-able (bỏ ``ctx.error`` — đó là Exception)."""
    errors = getattr(exc, "errors", None)
    if not callable(errors):  # pragma: no cover - phòng khi không phải ValidationError
        return [{"loc": [], "msg": str(exc), "type": "value_error"}]
    return [
        {"loc": [str(part) for part in item.get("loc", ())], "msg": item.get("msg", ""), "type": item.get("type", "")}
        for item in errors()
    ]
