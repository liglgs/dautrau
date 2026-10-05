"""Cấu hình pipeline ELT (đường dẫn, hằng số, đọc dataset-spec)."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ELT = DATA / "elt"
RAW_ROOT = ELT / "raw"
STAGING = ELT / "staging"
MANIFESTS = ELT / "manifests"
REPORTS = ELT / "reports"
SPEC_PATH = ELT / "dataset-spec.json"
BUNDLE_ZIP = DATA / "mvp-candidates-50-2026-10-02.zip"
BUNDLE_DIR = DATA / "mvp-candidates-50-2026-10-02"
RESEARCH_DIR = ROOT / "docs" / "research" / "2026-10-05" / "data-real"

USER_AGENT = "VigiLens-ELT/1.0 (+https://github.com/kp21-tech/nbtvfdcvbhtyjgtref; research pipeline)"

HOST_INTERVAL = {
    "eutils.ncbi.nlm.nih.gov": 0.35,
    "dailymed.nlm.nih.gov": 0.6,
    "api.fda.gov": 0.6,
    "www.accessdata.fda.gov": 0.6,
    "www.who.int": 0.6,
    "drive.google.com": 0.6,
}
DEFAULT_INTERVAL = 0.6
MAX_BYTES = 32 * 1024 * 1024


def load_spec(path: Path | None = None) -> dict:
    return json.loads((path or SPEC_PATH).read_text(encoding="utf-8"))


def pairs(spec: dict | None = None) -> list[dict]:
    return list((spec or load_spec()).get("pairs", []))


def bundle_spec(spec: dict | None = None) -> dict:
    return dict((spec or load_spec()).get("bundle", {}))


def ensure_dirs() -> None:
    for directory in (RAW_ROOT, STAGING, MANIFESTS, REPORTS):
        directory.mkdir(parents=True, exist_ok=True)


def ncbi_api_key() -> str:
    return (os.environ.get("NCBI_API_KEY") or "").strip()


def ncbi_email() -> str:
    return (os.environ.get("NCBI_EMAIL") or "vigilens-elt@example.invalid").strip()
