"""Loader cho bộ mock fixture M01 (dùng chung với demo mode của agent).

Dữ liệu nằm cùng thư mục này; logic đọc/kiểm tra nằm ở ``src/agents/mock_runtime.py``.
"""

from __future__ import annotations

from typing import Any

from src.agents.mock_runtime import FIXTURE_NAMES as NAMES
from src.agents.mock_runtime import load_fixture as load


def load_all() -> dict[str, dict[str, Any]]:
    return {name: load(name) for name in NAMES}
