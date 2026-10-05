"""Test local Person 3 files against fetched main without merging or clearing stash."""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from apply_person3_integration import apply

ROOT = Path(__file__).resolve().parents[1]
OVERLAYS = (
    "src/services/evidence", "tests/test_evidence", "tests/fixtures/mvp/person3",
    "data/dictionaries", "data/templates", "scripts/preview_person3.py", "scripts/preview_person3_integration.py",
    "scripts/demo_person3_scenarios.py",
    "src/prompts/extract_evidence.system.md", "src/prompts/extract_evidence.user.md",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--preview", action="store_true", help="Generate a synthetic draft in eval/person3 after testing")
    parser.add_argument("--scenarios", action="store_true", help="Show eight Person 3 input/output scenarios after testing")
    args = parser.parse_args()
    revision = subprocess.run(["git", "rev-parse", "--verify", f"{args.ref}^{{commit}}"],
                              cwd=ROOT, capture_output=True, check=True, text=True).stdout.strip()
    archive = subprocess.run(["git", "archive", "--format=zip", revision],
                             cwd=ROOT, capture_output=True, check=True).stdout
    snapshot = Path(tempfile.mkdtemp(prefix="p066-person3-check-"))
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for name in bundle.namelist():
            if not (snapshot / name).resolve().is_relative_to(snapshot.resolve()):
                raise ValueError("Unsafe archive entry")
        bundle.extractall(snapshot)
    apply(snapshot)
    for relative in OVERLAYS:
        source, destination = ROOT / relative, snapshot / relative
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        elif source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    print(f"MAIN_REF={revision}", flush=True)
    print(f"SNAPSHOT={snapshot}", flush=True)
    if args.prepare_only:
        return 0
    runtime = ROOT / ".local-preview/python-runtime"
    paths = [str(runtime), str(snapshot)] if runtime.is_dir() else [str(snapshot)]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(paths), "PYTHONIOENCODING": "utf-8",
           "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}
    command = [sys.executable, "-m", "pytest", "--confcutdir=tests/test_evidence",
               "tests/test_evidence", "tests/test_models/test_mvp_contracts.py",
               "tests/test_services/test_llm_gateway.py", "tests/test_services/test_prompt_contracts.py",
               "-q", "-p", "no:cacheprovider", "--tb=short",
               "--basetemp", str(snapshot / ".test-tmp"),
               "--ignore=tests/test_evidence/test_person3_runtime.py"]
    result = subprocess.run(command, cwd=snapshot, env=env).returncode
    if result == 0 and args.preview:
        result = subprocess.run([sys.executable, "scripts/preview_person3_integration.py", "--output-dir",
                                str(ROOT / "eval/person3")], cwd=snapshot, env=env).returncode
    if result == 0 and args.scenarios:
        result = subprocess.run([sys.executable, "scripts/demo_person3_scenarios.py", "--output-dir",
                                 str(ROOT / "eval/person3/scenarios")], cwd=snapshot, env=env).returncode
    return result


if __name__ == "__main__":
    raise SystemExit(main())
