"""Serve Person 3 synthetic runtime with a disposable DB for Person 4 browser tests."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
                "INVESTIGATOR_TOKEN": "person4-integration-investigator",
                "REVIEWER_TOKEN": "person4-integration-reviewer",
                "LANGSMITH_TRACING": "false",
                "LANGCHAIN_TRACING_V2": "false",
            }
        )
        import uvicorn

        from src.api.mvp_runtime import reset_mvp
        from src.main import app

        try:
            uvicorn.run(app, host="127.0.0.1", port=args.port)
        finally:
            reset_mvp()


if __name__ == "__main__":
    main()
