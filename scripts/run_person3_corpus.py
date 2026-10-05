"""Start the existing UI/API with frozen real sources and Person 3 services."""

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))


def main():
    from src.services.evidence.corpus_runtime import DEFAULT_BUNDLE, make_corpus_runtime

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["ibuprofen", "metformin", "lisinopril", "atorvastatin", "amoxicillin"], default="metformin")
    parser.add_argument("--provider", choices=["offline", "transport"], default="offline",
                        help="offline: uncertain lexical quotes; transport: configured model, charged calls")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.update({"MVP_EVIDENCE_MODE": "fixture", "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"})
    os.environ.setdefault("INVESTIGATOR_TOKEN", "person3-investigator-demo")
    os.environ.setdefault("REVIEWER_TOKEN", "person3-reviewer-demo")
    from src.config import get_settings
    get_settings.cache_clear()
    from src.main import app
    from src.api.mvp_runtime import configure_mvp
    from src.services.runner import configure_runner
    executor, gateway = make_corpus_runtime(args.family, bundle=args.bundle, provider=args.provider)
    # Configure before lifespan: its idempotent configure_mvp call preserves this runner.
    store = configure_mvp(str(ROOT / f"data/person3-corpus-{args.family}-{args.provider}.sqlite3"), force=True)
    configure_runner(store, executor=executor, gateway=gateway)
    import uvicorn
    print(f"Person 3: REAL frozen sources / {args.provider} provider / {args.family}; http://127.0.0.1:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
