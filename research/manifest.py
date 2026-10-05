"""Stable hashes for the benchmark inputs and evaluator labels."""

import hashlib
import json

from research.fixtures import ResearchCase
from src.vmec import PRODUCTS


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_manifest(dev: list[ResearchCase], test: list[ResearchCase]) -> dict:
    return {
        "dataset_version": "vmec03-synthetic-1",
        "schema_version": "1.0", "catalog_version": _digest(PRODUCTS), "seed": 6603,
        "cases": [{"case_id": case.case_id, "split": case.split, "group": case.group,
                   "family_id": case.family_id,
                   "sha256": _digest({"initial_sources": case.initial_sources,
                                      "delayed_sources": case.delayed_sources, "labels": case.labels})}
                  for case in dev + test],
    }
