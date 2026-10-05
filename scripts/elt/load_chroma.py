"""Dựng hoặc kiểm tra chỉ mục RAG (ChromaDB) từ kho ELT.

Ví dụ:
    python -m scripts.elt.load_chroma --reset --provider auto
    python -m scripts.elt.load_chroma --provider hash --limit 20
    python -m scripts.elt.load_chroma --stats
"""

from __future__ import annotations

import argparse
import json
import sys

from src.config import get_settings
from src.services.rag import build as rag_build
from src.services.warehouse import db as wh_db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dựng chỉ mục RAG cho kho ELT")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--pair-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--include-quarantine", action="store_true")
    parser.add_argument("--provider", choices=["auto", "gemini", "hash"], default=None)
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--run-id", default="manual-chroma")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.provider:
        settings = settings.model_copy(update={"rag_embedding_provider": args.provider})
    engine = wh_db.get_warehouse_engine()
    if args.stats:
        print(json.dumps(rag_build.index_stats(engine, settings), indent=2, ensure_ascii=False))
        return 0
    stats = rag_build.build_index(
        engine, run_id=args.run_id, pair_id=args.pair_id, only_keep=not args.include_quarantine,
        reset=args.reset, limit=args.limit, settings=settings,
    )
    stats["index_stats"] = rag_build.index_stats(engine, settings)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
