"""Prepare a review packet, or publish explicitly adjudicated labels to P26."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))

from eval.person3_dataset import export_dataset  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "data/mvp-candidates-50-2026-10-02.zip")
    parser.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmark")
    parser.add_argument("--output", type=Path, default=ROOT / "data/person3/evaluation-review")
    parser.add_argument("--approval", type=Path, help="Specialist freeze approval with final annotations and input hashes")
    args = parser.parse_args()
    report = export_dataset(args.bundle, args.benchmark, args.output, approval=args.approval)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Prepared review data. Clinical metrics require independent labels and explicit adjudication.")


if __name__ == "__main__":
    main()
