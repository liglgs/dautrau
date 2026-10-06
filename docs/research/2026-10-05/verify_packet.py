"""Kiểm bộ nghiên cứu 05/10/2026: băm 18 payload, cấu trúc fragment, health dịch vụ.

Chạy được trên máy mới (Linux/macOS/Windows):

    python docs/research/2026-10-05/verify_packet.py                 # kiểm băm + health
    python docs/research/2026-10-05/verify_packet.py --fragment <đường-dẫn.html>

Phần fragment (prototype `preview.html`) chỉ chạy khi tìm thấy tệp HTML nguồn.
Tệp gốc nằm ngoài repo (đường dẫn Windows của phiên làm việc cũ), nên nếu không
truyền `--fragment` thì script bỏ qua phần đó và nói rõ là đã bỏ qua — không
làm hỏng phần kiểm băm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).parent
DATA = ROOT / "data-real"


def check_manifest() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    verified = [row for row in manifest if row["verified_payload"]]
    assert len(verified) == 18
    assert len({row["id"] for row in manifest}) == len(manifest)
    normalized: list[str] = []
    for row in verified:
        digest = hashlib.sha256((DATA / row["file"]).read_bytes()).hexdigest()
        if digest == row["sha256"]:
            continue
        # Tệp được lưu lại khi nhập repo (đổi xuống dòng); manifest ghi băm của bản cam kết.
        assert digest == row.get("sha256_committed"), f"lệch băm: {row['file']}"
        normalized.append(row["file"])
    print(f"18 payload hashes OK; manifest IDs unique ({len(normalized)} tệp chuẩn hoá khi nhập repo)")


def check_fragment(fragment_path: Path) -> None:
    fragment = fragment_path.read_text(encoding="utf-8")
    assert len(fragment.encode()) < 1000000
    assert not re.search(r"<!doctype|<html|<body|<head>|fetch\(|XMLHttpRequest|WebSocket", fragment, re.I)
    assert '\\"' not in fragment and r"\n" not in fragment
    script = re.search(r"<script>(.*?)</script>", fragment, re.S)[1]
    (ROOT / "proposal-script.js").write_text(script, encoding="utf-8")
    print("Fragment structure OK")


def check_services() -> None:
    for url in ["http://127.0.0.1:8000/health", "http://127.0.0.1:3100/login"]:
        response = httpx.get(url, timeout=20)
        print(url, response.status_code)
        assert response.status_code == 200


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fragment",
        type=Path,
        default=None,
        help="Tệp HTML chứa prototype cần kiểm cấu trúc (bỏ qua nếu không truyền).",
    )
    parser.add_argument(
        "--skip-services",
        action="store_true",
        help="Bỏ qua bước kiểm health dịch vụ (dùng khi backend/giao diện chưa chạy).",
    )
    args = parser.parse_args(argv)

    check_manifest()
    if args.fragment is not None:
        if not args.fragment.exists():
            print(f"BỎ QUA phần fragment: không thấy {args.fragment}")
        else:
            check_fragment(args.fragment)
    else:
        print("BỎ QUA phần fragment: không truyền --fragment (tệp gốc nằm ngoài repo).")
    if args.skip_services:
        print("BỎ QUA phần health dịch vụ (--skip-services).")
    else:
        check_services()
    return 0


if __name__ == "__main__":
    sys.exit(main())
