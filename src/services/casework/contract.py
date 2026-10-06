"""Đối chiếu tài liệu của tầng casework với hợp đồng đóng băng ``hospital-v2``.

``docs/contracts-hospital-v2.md`` giao cho tầng này việc bảo đảm tài liệu đúng lược đồ. Việc kiểm
nằm ở đây chứ không nằm trong tệp tuyến, vì **cả hai đầu** đều cần: đầu ghi để hàng sai không vào
được kho, và đầu đọc để hàng sai đã lỡ nằm trong kho không ra tới khách.

Gói bằng chứng là tài liệu duy nhất đi thẳng từ kho ra mà **không** qua một mô hình Pydantic nào —
hình dạng của nó do bên ghi quyết định — nên đây là chỗ phải soi bằng chính tệp lược đồ.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

#: Lược đồ đóng băng của hợp đồng ``hospital-v2``. Đọc một lần lúc nạp mô-đun: tệp này là hợp đồng,
#: không phải cấu hình, nên thiếu nó là lỗi dựng chương trình chứ không phải lỗi chạy.
_SCHEMAS_PATH = Path(__file__).resolve().parents[3] / "docs" / "spec" / "hospital-v2" / "schemas.json"


@lru_cache(maxsize=1)
def contract_schemas() -> dict[str, Any]:
    """Toàn bộ ``schemas.json``, đọc một lần cho cả tiến trình."""
    return json.loads(_SCHEMAS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=32)
def _validator(name: str) -> Draft202012Validator:
    """Bộ kiểm cho một định nghĩa trong ``$defs``, kèm toàn bộ ``$defs`` để tham chiếu chéo chạy được."""
    schemas = contract_schemas()
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": schemas["$defs"]})


def contract_violations(name: str, document: Any) -> list[str]:
    """Đường dẫn JSON của những chỗ tài liệu sai ``schemas.json``, rỗng nếu khớp.

    Không chuẩn hoá và không suy diễn: trường mà kho không có thì không suy ra được, và bịa ra đúng
    là loại dữ liệu giả mà hợp đồng này sinh ra để chặn.
    """
    return [
        f"{'/'.join(str(part) for part in error.path) or '<gốc>'}: {error.message}"
        for error in sorted(_validator(name).iter_errors(document), key=lambda item: list(item.path))
    ]
