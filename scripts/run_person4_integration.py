"""Serve Person 3 synthetic runtime with a disposable DB for Person 4 browser tests.

AUTH-01: cầu nối giao diện không còn nhận vai do trình duyệt khai, nên bài kiểm thử tích hợp phải
đăng nhập thật. Máy chủ này nạp sẵn hai tài khoản nội bộ dưới đây (chỉ ở APP_ENV=test).
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INVESTIGATOR_EMAIL = "person4-integration-investigator@example.test"
REVIEWER_EMAIL = "person4-integration-reviewer@example.test"
INTEGRATION_PASSWORD = "person4-integration-password"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8203)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory(prefix="p066-person4-integration-") as folder:
        os.environ.update(
            {
                "APP_ENV": "test",
                "MVP_DB_PATH": str(Path(folder) / "integration.sqlite3"),
                "MVP_EVIDENCE_MODE": "person3_demo",
                "MVP_PERSON3_DEMO_SCENARIO": "match",
                "LANGSMITH_TRACING": "false",
                "LANGCHAIN_TRACING_V2": "false",
            }
        )
        import uvicorn

        from src.api.auth import hash_password
        from src.api.mvp_runtime import get_mvp_store, reset_mvp
        from src.main import app

        store = get_mvp_store()
        for user_id, email, role in (
            ("usr_p4_dieu_tra", INVESTIGATOR_EMAIL, "investigator"),
            ("usr_p4_duyet", REVIEWER_EMAIL, "reviewer"),
        ):
            store.create_user(
                user_id=user_id,
                email=email,
                role=role,
                display_name=email,
                password_hash=hash_password(INTEGRATION_PASSWORD),
                created_by="person4-integration",
                actor_role="integration",
            )

        try:
            uvicorn.run(app, host="127.0.0.1", port=args.port)
        finally:
            reset_mvp()


if __name__ == "__main__":
    main()
