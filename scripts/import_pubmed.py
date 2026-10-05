"""Import a PubMed Save -> PubMed UTF-8 export into the explicit local corpus."""

import argparse
import json
import sys

from src.services.sources.pubmed_local import import_pubmed_file
from src.services.sources.transport import SourceError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--corpus-root", default="data/pubmed-local")
    parser.add_argument("--query", required=True, help="Original browser search query for provenance")
    args = parser.parse_args()
    try:
        docs = import_pubmed_file(args.input, args.corpus_root, query=args.query)
    except (SourceError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PubMed import failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"imported_pmids": [d.source_id for d in docs], "corpus_root": args.corpus_root}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
