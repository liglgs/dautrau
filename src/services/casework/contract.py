"""Đối chiếu tài liệu của tầng casework với hợp đồng đóng băng ``hospital-v2``.

``docs/contracts-hospital-v2.md`` giao cho tầng này việc bảo đảm tài liệu đúng lược đồ. Việc kiểm
nằm ở đây chứ không nằm trong tệp tuyến, vì **cả hai đầu** đều cần: đầu ghi để hàng sai không vào
được kho, và đầu đọc để hàng sai đã lỡ nằm trong kho không ra tới khách.

Gói bằng chứng là tài liệu duy nhất đi thẳng từ kho ra mà **không** qua một mô hình Pydantic nào —
hình dạng của nó do bên ghi quyết định — nên đây là chỗ phải soi bằng chính tệp lược đồ.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, validators

#: Lược đồ đóng băng của hợp đồng ``hospital-v2``. Đọc một lần lúc nạp mô-đun: tệp này là hợp đồng,
#: không phải cấu hình, nên thiếu nó là lỗi dựng chương trình chứ không phải lỗi chạy.
_SCHEMAS_PATH = Path(__file__).resolve().parents[3] / "docs" / "spec" / "hospital-v2" / "schemas.json"


def _is_rfc3339_datetime(value: Any) -> bool:
    """``Timestamp`` của hợp đồng là "RFC 3339, luôn có múi giờ" — kiểm đúng như vậy.

    Vì sao phải tự kiểm: ``jsonschema`` coi ``format`` là **chú thích** trừ khi có gói kiểm định dạng
    tương ứng, và gói ``rfc3339-validator`` không nằm trong phụ thuộc. Đo được: với bộ kiểm mặc định,
    ``created_at: "khong-phai-ngay"`` **hợp lệ**. Không thêm gói mới chỉ để kiểm một trường, nên dùng
    thư viện chuẩn.

    ``fromisoformat`` một mình chưa đủ chặt: nó nhận cả ``"2026-01-01"`` (ngày trần, không có giờ) và
    trả về nửa đêm. Nên phải đòi có phần giờ **và** có múi giờ.
    """
    if not isinstance(value, str):
        return True  # kiểu đã do ``type: string`` lo; ở đây chỉ kiểm định dạng
    if "T" not in value and "t" not in value:
        return False
    # RFC 3339 cho phép ``t``/``z`` viết thường, nhưng ``datetime.fromisoformat`` chỉ nhận ``Z``.
    # Chuẩn hoá hai ký tự đó trước khi phân tích; không có chỗ nào khác trong RFC 3339 dùng chữ cái.
    normalised = value.replace("t", "T").replace("z", "Z")
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return False
    return parsed.tzinfo is not None


#: Bộ kiểm định dạng **riêng của mô-đun này**. ``FormatChecker.__init__`` sao ``checkers`` ra thành
#: thuộc tính của từng thực thể, nên đăng ký ở đây không sửa luật dùng chung của cả tiến trình.
_FORMAT_CHECKER = FormatChecker()
_FORMAT_CHECKER.checks("date-time")(_is_rfc3339_datetime)

#: ``integer`` theo nghĩa **Python**, không theo nghĩa JSON Schema.
#:
#: JSON Schema 2020-12 coi ``1.0`` là một số nguyên (số có phần thập phân bằng không), nên lược đồ
#: cho nó qua. Nhưng tầng API dùng Pydantic ``strict=True`` và **từ chối** đúng giá trị đó. Đo được
#: trước khi sửa: cùng một tài liệu bị API trả 422 mà cửa ghi vẫn nhận và ghi ``1.0`` vào kho. Một
#: luật cho cả hai đầu thì phải là luật chặt hơn, nếu không thì "một luật" chỉ đúng trên giấy.
_TYPE_CHECKER = Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, instance: isinstance(instance, int) and not isinstance(instance, bool)
)
_Validator = validators.extend(Draft202012Validator, type_checker=_TYPE_CHECKER)


@lru_cache(maxsize=1)
def contract_schemas() -> dict[str, Any]:
    """Toàn bộ ``schemas.json``, đọc một lần cho cả tiến trình."""
    return json.loads(_SCHEMAS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=32)
def _validator(name: str) -> Draft202012Validator:
    """Bộ kiểm cho một định nghĩa trong ``$defs``, kèm toàn bộ ``$defs`` để tham chiếu chéo chạy được."""
    schemas = contract_schemas()
    return _Validator(
        {"$ref": f"#/$defs/{name}", "$defs": schemas["$defs"]}, format_checker=_FORMAT_CHECKER
    )


def contract_violations(name: str, document: Any) -> list[str]:
    """Đường dẫn JSON của những chỗ tài liệu sai ``schemas.json``, rỗng nếu khớp.

    Không chuẩn hoá và không suy diễn: trường mà kho không có thì không suy ra được, và bịa ra đúng
    là loại dữ liệu giả mà hợp đồng này sinh ra để chặn.
    """
    return [
        f"{'/'.join(str(part) for part in error.path) or '<gốc>'}: {error.message}"
        for error in sorted(_validator(name).iter_errors(document), key=lambda item: list(item.path))
    ]
