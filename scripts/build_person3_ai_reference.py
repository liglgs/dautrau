"""Build the reviewed AI silver reference without changing expert annotation files."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / ".local-preview/python-runtime").is_dir():
    sys.path.insert(0, str(ROOT / ".local-preview/python-runtime"))

from eval.person3_provisional import build_ai_reference  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "data/mvp-candidates-50-2026-10-02.zip")
    parser.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmark")
    parser.add_argument("--output", type=Path, default=ROOT / "data/person3/evaluation-ai")
    args = parser.parse_args()
    result = build_ai_reference(args.bundle, args.benchmark, args.output)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
