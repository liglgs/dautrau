"""Explicit offline retrieval from immutable PubMed browser exports, not gold mappings."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.models.schemas import SourceDocument
from src.services.sources.base import SourceAdapter
from src.services.sources.parser import document
from src.services.sources.transport import SourceError

MAX_EXPORT_BYTES = 4_000_000
MAX_MANIFEST_BYTES = 20_000_000
MAX_DOCUMENTS = 1000
FORMAT = "pubmed-local-v1"


def _read(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise SourceError("parse_error: local corpus size limit exceeded")
    return raw


def _records(raw: bytes) -> list[dict[str, list[str]]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceError("parse_error: export must be UTF-8") from exc
    records = []
    fields: dict[str, list[str]] = {}
    key = None
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([A-Z0-9]{2,4})\s*-\s?(.*)", line)
        if match:
            key, value = match.groups()
            if key == "PMID":
                if fields:
                    records.append(fields)
                fields = {}
            elif not fields:
                raise SourceError("parse_error: record must start with PMID")
            fields.setdefault(key, []).append(value)
        elif key and line.startswith("      "):
            fields[key][-1] += " " + line.strip()
        else:
            raise SourceError("parse_error: invalid tagged export line")
    if fields:
        records.append(fields)
    if not records or len(records) > MAX_DOCUMENTS:
        raise SourceError("parse_error: empty export or too many records")
    for record in records:
        if len(record.get("PMID", [])) != 1 or not re.fullmatch(r"[0-9]+", record["PMID"][0]):
            raise SourceError("parse_error: invalid PMID")
        if not " ".join(record.get("TI", [])).strip():
            raise SourceError("parse_error: missing article title")
    if len({record["PMID"][0] for record in records}) != len(records):
        raise SourceError("parse_error: duplicate PMID in raw export")
    return records


def _raw_path(root: Path, ref: str) -> Path:
    relative = Path(ref)
    if relative.is_absolute() or ".." in relative.parts:
        raise SourceError("parse_error: raw path outside corpus")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise SourceError("parse_error: raw path outside corpus")
    return path


def _record_document(record: dict[str, list[str]], raw: bytes) -> SourceDocument:
    """Derive citation content and bibliographic metadata only from the raw export."""
    pmid = record["PMID"][0]
    abstract = " ".join(record.get("AB", []))
    return document(
        "pubmed",
        pmid,
        1,
        " ".join(record["TI"]),
        f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        raw,
        [("Abstract", abstract)] if abstract else [],
        {
            "content_level": "abstract_only" if abstract else "metadata_only",
            "doi": [v.removesuffix(" [doi]") for v in record.get("AID", []) if v.endswith(" [doi]")],
            "publication_date": record.get("DP", []),
            "publication_types": record.get("PT", []),
            "authors": record.get("AU", []),
            "journal": record.get("JT", []),
            "source_record_version": None,
            "version_semantics": "local_collection_version",
            "warnings": ["source_revision_unknown", *(["missing_abstract"] if not abstract else [])],
        },
    )


def _load(root: Path) -> list[SourceDocument]:
    payload = json.loads(_read(root / "manifest.json", MAX_MANIFEST_BYTES))
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise SourceError("parse_error: unsupported local corpus manifest")
    rows = payload.get("documents")
    if not isinstance(rows, list) or len(rows) > MAX_DOCUMENTS:
        raise SourceError("parse_error: invalid corpus documents")
    docs = [SourceDocument.model_validate(row) for row in rows]
    if len({d.source_id for d in docs}) != len(docs):
        raise SourceError("parse_error: duplicate corpus PMID")
    for d in docs:
        if d.source != "pubmed" or not d.source_id.isdigit():
            raise SourceError("parse_error: invalid corpus source")
        raw = _read(_raw_path(root, d.metadata["raw_ref"]), MAX_EXPORT_BYTES)
        if hashlib.sha256(raw).hexdigest() != d.metadata["raw_hash"]:
            raise SourceError("parse_error: corrupt corpus raw snapshot")
        digest = hashlib.sha256(d.text.encode()).hexdigest()
        if digest != d.hash or digest != d.metadata["parsed_hash"]:
            raise SourceError("parse_error: corrupt corpus parsed text")
        records = [record for record in _records(raw) if record["PMID"][0] == d.source_id]
        if len(records) != 1:
            raise SourceError("parse_error: missing or duplicate PMID in raw export")
        expected = _record_document(records[0], raw)
        fields = ("doc_id", "source", "source_id", "version", "title", "source_url", "text", "hash")
        if any(getattr(d, field) != getattr(expected, field) for field in fields) or any(
            d.metadata.get(key) != value for key, value in expected.metadata.items()
        ):
            raise SourceError("parse_error: corpus content does not match raw export")
        for section in d.metadata.get("sections", []):
            if not 0 <= section["start"] < section["end"] <= len(d.text):
                raise SourceError("parse_error: invalid corpus section locator")
    return docs


def import_pubmed_file(input_path: str | Path, corpus_root: str | Path, *, query: str) -> list[SourceDocument]:
    """Import Save -> PubMed text. Conflicting PMID content requires a new corpus root."""
    source, root = Path(input_path), Path(corpus_root)
    raw = _read(source, MAX_EXPORT_BYTES)
    records = _records(raw)
    digest = hashlib.sha256(raw).hexdigest()
    existing = _load(root) if (root / "manifest.json").exists() else []
    by_id = {d.source_id: d for d in existing}
    imported = []
    for record in records:
        pmid = record["PMID"][0]
        doc = _record_document(record, raw)
        doc.metadata.update(
            {
                "raw_ref": f"raw/{digest}.txt",
                "raw_format": "PubMed_tagged_text",
                "raw_record_locator": {"pmid": pmid, "method": "PMID tag in batch export"},
                "import_query": query,
                "imported_at": datetime.now(UTC).isoformat(),
                "original_file": source.name,
                "acquisition_method": "browser_export",
            },
        )
        prior = by_id.get(pmid)
        if prior is not None:
            same_metadata = all(
                prior.metadata.get(key) == doc.metadata[key]
                for key in ("doi", "publication_date", "publication_types", "authors", "journal")
            )
            if prior.hash != doc.hash or not same_metadata:
                raise SourceError(f"parse_error: conflicting PMID {pmid}; use a new corpus root")
        else:
            by_id[pmid] = doc
        imported.append(by_id[pmid])
    if len(by_id) > MAX_DOCUMENTS:
        raise SourceError("parse_error: too many corpus documents")
    manifest = json.dumps(
        {"format": FORMAT, "documents": [d.model_dump(mode="json") for d in by_id.values()]},
        ensure_ascii=False,
        indent=2,
    ).encode()
    if len(manifest) > MAX_MANIFEST_BYTES:
        raise SourceError("parse_error: local corpus size limit exceeded")
    raw_path = root / "raw" / f"{digest}.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists():
        if _read(raw_path, MAX_EXPORT_BYTES) != raw:
            raise SourceError("parse_error: corrupt corpus raw snapshot")
    else:
        raw_path.write_bytes(raw)
    temporary = root / f".{uuid4().hex}.tmp"
    try:
        temporary.write_bytes(manifest)
        os.replace(temporary, root / "manifest.json")
    finally:
        temporary.unlink(missing_ok=True)
    return imported


def _tokens(text: str) -> list[str]:
    aliases = {"diarrhoea": "diarrhea", "haemorrhage": "hemorrhage"}
    return [aliases.get(t, t) for t in re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())]


class LocalPubMedAdapter(SourceAdapter):
    name = "pubmed"

    def __init__(self, *, corpus_root: str | Path, **options):
        super().__init__(**options)
        self.corpus_root = Path(corpus_root)

    def search_with_budget(self, action, budget, on_request=None):
        # Read and verify each search; local corpus edits must not bypass validation through cache.
        self._cache.clear()
        return super().search_with_budget(action, budget, on_request)

    def fetch(self, action, meter):
        query = action.query or ""
        if re.search(r"[\[\]:()\"]|\b(?:AND|OR|NOT)\b", query):
            raise SourceError("invalid_query: local retrieval accepts plain text, not PubMed query syntax")
        terms = set(_tokens(query))
        if not terms:
            raise SourceError("invalid_query: empty local query")
        docs = _load(self.corpus_root)
        counts = [Counter(_tokens(d.text)) for d in docs]
        average = sum(sum(c.values()) for c in counts) / len(counts) if counts else 1
        frequencies = {t: sum(t in c for c in counts) for t in terms}
        ranked = []
        for d, counts_doc in zip(docs, counts):
            if not terms.issubset(counts_doc):
                continue
            score = 0.0
            for term in terms:
                freq = counts_doc[term]
                idf = math.log(1 + (len(docs) - frequencies[term] + 0.5) / (frequencies[term] + 0.5))
                score += idf * freq * 2.2 / (freq + 1.2 * (0.25 + 0.75 * sum(counts_doc.values()) / average))
            score += len(terms.intersection(_tokens(d.title)))
            ranked.append((score, d))
        ranked.sort(key=lambda item: (-item[0], item[1].source_id))
        results = []
        for score, d in ranked[: self.max_documents]:
            copy = d.model_copy(deep=True)
            copy.metadata.update(
                retrieval_method="local_lexical",
                retrieval_query=query,
                retrieval_score=score,
                corpus_root=str(self.corpus_root),
                local_corpus_size=len(docs),
            )
            copy.metadata["warnings"] = [*copy.metadata.get("warnings", []), "local_corpus_not_live_pubmed"]
            raw = _read(_raw_path(self.corpus_root, d.metadata["raw_ref"]), MAX_EXPORT_BYTES)
            results.append(self.snapshot(copy, raw))
        return results
