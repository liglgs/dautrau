"""Xuất OpenAPI của backend MVP ra ``docs/openapi.json`` (P20).

Người 4 dùng file này để sinh types cho UI Next.js thay vì đoán hình dạng response.

    python scripts/export_openapi.py            # ghi docs/openapi.json
    python scripts/export_openapi.py --check    # chỉ kiểm tra file đang khớp
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.main import app  # noqa: E402

OUTPUT = ROOT / "docs" / "openapi.json"


def render() -> str:
    schema = app.openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Xuất OpenAPI schema của backend MVP.")
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm tra docs/openapi.json có khớp không.")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Đường dẫn file đầu ra.")
    args = parser.parse_args()

    content = render()
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != content:
            print(f"OpenAPI lệch với {args.output}; chạy lại không có --check.")
            return 1
        print("OpenAPI khớp.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Đã ghi {args.output} ({len(content)} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
