"""Immutable evidence-unit corpus. Gold labels never enter this module."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class IntegrityError(ValueError):
    pass


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def timestamp(raw: str) -> datetime:
    if not isinstance(raw, str) or not raw.strip():
        raise IntegrityError("Timestamp must be a nonempty string with timezone")
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise IntegrityError("Cutoff/available_at must include timezone")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@dataclass(frozen=True)
class Unit:
    unit_id: str
    doc_id: str
    source: str
    source_id: str
    version: int
    title: str
    text: str
    document_hash: str
    available_at: str
    start: int
    end: int

    def public_view(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class Corpus:
    units: tuple[Unit, ...]
    manifest_hash: str
    cutoff: str
    synthetic: bool
    versions: dict[str, str]

    @classmethod
    def load(cls, manifest_path: Path) -> Corpus:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw)
        if not isinstance(manifest, dict):
            raise IntegrityError("Corpus manifest must be an object")
        if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
            raise IntegrityError("Unsupported corpus schema_version; expected integer 1")
        if type(manifest.get("synthetic")) is not bool:
            raise IntegrityError("Corpus synthetic must be boolean")
        if manifest.get("mode") != "replay":
            raise IntegrityError("Only replay manifests are accepted")
        cutoff = timestamp(manifest["cutoff"])
        root = manifest_path.parent.resolve()
        units: list[Unit] = []
        seen_docs: set[str] = set()
        seen_versions: set[tuple[str, str, int]] = set()
        seen_units: set[str] = set()
        for document in manifest["documents"]:
            path = (root / document["path"]).resolve()
            if not path.is_relative_to(root):
                raise IntegrityError("Snapshot path leaves corpus directory")
            content = path.read_bytes()
            if digest(content) != document["sha256"]:
                raise IntegrityError(f"Snapshot hash mismatch: {document['doc_id']}")
            text = content.decode("utf-8")
            available_at = document["available_at"]
            if timestamp(available_at) > cutoff:
                raise IntegrityError("Future document in retrieval corpus")
            source = document["source"]
            if source not in {"pubmed", "dailymed", "faers"}:
                raise IntegrityError("Unknown source")
            doc_id = document["doc_id"]
            version = document["version"]
            if any(not isinstance(value, str) or not value.strip() for value in (doc_id, document["source_id"])):
                raise IntegrityError("Source document identity must be nonempty strings")
            if type(version) is not int or version < 1:
                raise IntegrityError("Source document version must be a positive integer")
            identity = (source, document["source_id"], version)
            if doc_id in seen_docs or identity in seen_versions:
                raise IntegrityError("Duplicate document/version")
            seen_docs.add(doc_id)
            seen_versions.add(identity)
            for unit in document["units"]:
                start, end = unit["start"], unit["end"]
                if type(start) is not int or type(end) is not int:
                    raise IntegrityError("Evidence locator must use integer Unicode code-point offsets")
                if not 0 <= start < end <= len(text) or text[start:end] != unit["text"]:
                    raise IntegrityError("Evidence locator does not match snapshot")
                if not isinstance(unit["unit_id"], str) or not unit["unit_id"].strip():
                    raise IntegrityError("Evidence unit identity must be a nonempty string")
                if unit["unit_id"] in seen_units:
                    raise IntegrityError("Duplicate evidence unit ID")
                seen_units.add(unit["unit_id"])
                units.append(
                    Unit(
                        unit["unit_id"],
                        doc_id,
                        source,
                        document["source_id"],
                        version,
                        document.get("title", ""),
                        unit["text"],
                        document["sha256"],
                        available_at,
                        start,
                        end,
                    )
                )
        return cls(tuple(units), digest(raw), manifest["cutoff"], manifest["synthetic"], manifest.get("versions", {}))

    def visible(self, cutoff: str | None = None) -> tuple[Unit, ...]:
        requested = timestamp(cutoff or self.cutoff)
        if requested > timestamp(self.cutoff):
            raise IntegrityError("Claim cutoff exceeds frozen corpus cutoff")
        return tuple(unit for unit in self.units if timestamp(unit.available_at) <= requested)
