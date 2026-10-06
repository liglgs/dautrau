"""Start the shared backend with Person 3 enabled on synthetic sources/LLM."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))


def main():
    from src.services.evidence.demo import SCENARIOS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="match")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.update({
        "MVP_EVIDENCE_MODE": "person3_demo",
        "MVP_SOURCE_MODE": "fixture",
        "MVP_PERSON3_DEMO_SCENARIO": args.scenario,
        "MVP_DB_PATH": str(ROOT / "data/person3-demo.sqlite3"),
        "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false",
    })
    os.environ.setdefault("INVESTIGATOR_TOKEN", "person3-investigator-demo")
    os.environ.setdefault("REVIEWER_TOKEN", "person3-reviewer-demo")
    # Bản demo ngoại tuyến dùng khoá tĩnh cũ, mà khoá đó mặc định tắt từ B1.7.
    os.environ.setdefault("VIGILENS_ALLOW_LEGACY_TOKENS", "1")
    try:
        import uvicorn
        from src.main import app
        from src.config import get_settings
    except ImportError as error:
        raise SystemExit(
            f"Missing demo dependency: {error}. Install requirements-person3-demo.txt first."
        ) from None
    get_settings.cache_clear()
    print(f"Person 3 SYNTHETIC demo: scenario={args.scenario}; http://127.0.0.1:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
