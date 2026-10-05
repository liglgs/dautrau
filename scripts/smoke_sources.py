"""Explicit, small live retrieval probe; does not call an LLM or assess drug safety."""

import argparse
import json

from src.models.schemas import BudgetState, PlannerActionKind, PlannerDecision, SourceStatus
from src.services.sources import build_adapters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow requests to public source APIs")
    parser.add_argument("--drug", default="ibuprofen")
    parser.add_argument("--event", default="bleeding")
    parser.add_argument("--snapshot-root", default="data/snapshots")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to opt into public API calls; offline tests use pytest tests/test_sources")
    sources = build_adapters(drug=args.drug, event=args.event, max_documents=1, snapshot_root=args.snapshot_root)
    failed = False
    for source, adapter in sources.items():
        action = PlannerDecision(
            action=PlannerActionKind.SEARCH_SOURCE,
            source=source,
            query=f"{args.drug} {args.event}",
            reason="Small explicit live source smoke",
        )
        result = adapter.search(action, BudgetState(max_source_requests=8))
        print(
            json.dumps(
                {
                    "source": source,
                    "status": result.status,
                    "error": result.error,
                    "requests": result.requests_used,
                    "documents": [
                        {"id": d.doc_id, "hash": d.hash, "warnings": d.metadata.get("warnings", [])}
                        for d in result.documents
                    ],
                },
                ensure_ascii=True,
            ),
            flush=True,
        )
        failed = failed or result.status == SourceStatus.ERROR
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
