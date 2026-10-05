"""Test the merged checkout with isolated dotenv and no external network."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = [
    "tests/test_evidence", "tests/test_sources", "tests/test_models/test_mvp_contracts.py",
    "tests/test_agents/test_mvp_graph.py", "tests/test_services/test_mvp_runtime.py",
    "tests/test_services/test_llm_gateway.py", "tests/test_services/test_prompt_contracts.py",
    "tests/test_services/test_mvp_review.py", "tests/test_dossier/test_mvp_dossier.py",
    "tests/test_api/test_mvp_api.py",
]

# Execute pytest from an empty temporary directory. Settings and implicit dotenv
# discovery cannot read the checkout's private .env. Child CLI tests inherit the
# explicit PYTHONPATH and safe environment. Tests/conftest.py installs the network guard.
CHILD = '''
import os, sys
from pathlib import Path
import dotenv
original = dotenv.load_dotenv
def isolated_load(path=None, *args, **kwargs):
    if path is None and "dotenv_path" not in kwargs and "stream" not in kwargs:
        path = Path.cwd() / ".env"
    return original(path, *args, **kwargs)
dotenv.load_dotenv = isolated_load
import pytest
code = pytest.main(sys.argv[1:])
from src.api.mvp_runtime import reset_mvp
reset_mvp()
from src.db import engine
engine.dispose()
sys.exit(code)
'''


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Run all repository tests (live excluded).")
    args = parser.parse_args()
    runtime = ROOT / ".local-preview/python-runtime"
    paths = [str(runtime), str(ROOT)] if runtime.is_dir() else [str(ROOT)]
    blocked = ("GEMINI_", "OPENAI_", "MODEL_", "MVP_", "AI_LOG_", "LANGCHAIN_", "LANGSMITH_")
    env = {key: value for key, value in os.environ.items() if not key.startswith(blocked)}
    env.update(PYTHONPATH=os.pathsep.join(paths), PYTHONIOENCODING="utf-8", APP_ENV="test",
               LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false",
               MVP_EVIDENCE_MODE="fixture", MVP_SOURCE_MODE="fixture", DATABASE_URL="sqlite:///:memory:")
    targets = ["tests"] if args.all else DEFAULT_TARGETS
    with tempfile.TemporaryDirectory(prefix="p066-person3-merged-tests-") as folder:
        (Path(folder) / ".env").write_text("", encoding="utf-8")
        command = [sys.executable, "-c", CHILD, *(str(ROOT / path) for path in targets),
                   "-q", "-p", "no:cacheprovider", "--tb=short", "--basetemp", str(Path(folder) / "pytest")]
        result = subprocess.run(command, cwd=folder, env=env, capture_output=True, text=True, encoding="utf-8")
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
    summary = next((line for line in reversed(result.stdout.splitlines())
                    if re.search(r"\d+ (passed|failed)", line)), "")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0],
        "base_commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "checkout": "current working tree, including uncommitted changes", "all_repository_tests": args.all,
        "mode": "offline integration; authored HTTP/model responses", "targets": targets,
        "exit_code": result.returncode, "pytest_summary": summary,
        "dotenv_isolated": True, "external_network_blocked_by_pytest": True,
        "ui_browser_verified": False, "live_sources_or_llm_used": False, "clinical_gold_measured": False,
        "command": "python scripts/test_person3_backend.py" + (" --all" if args.all else ""),
    }
    output = ROOT / "eval/person3/merged-runtime-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
