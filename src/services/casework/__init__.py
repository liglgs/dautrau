"""Lưu trữ lát cắt DI: yêu cầu, liên kết điều tra, gói bằng chứng, phiếu trả lời, theo dõi.

Dùng cùng cơ sở dữ liệu với kho ELT (``elt_database_url``) nhưng khác bảng.
"""

from __future__ import annotations

from src.services.casework.store import (
    ALLOWED_WORK_ITEM_PATCH_FIELDS,
    CaseWorkStore,
    work_item_document,
)

__all__ = ["ALLOWED_WORK_ITEM_PATCH_FIELDS", "CaseWorkStore", "work_item_document"]
