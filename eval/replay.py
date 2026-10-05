"""Source adapter for RunContext.adapters, using the common BM25 corpus without gold."""

from __future__ import annotations

import json
from pathlib import Path

from eval.baselines.keyword import BM25
from eval.corpus import IntegrityError, digest
from src.models.schemas import BudgetState, PlannerDecision, SourceDocument, SourceSearchResult, SourceStatus
from src.services.planner import query_fingerprint


class ReplayAdapter:
    def __init__(self, name: str, index: BM25, manifest: Path, *, cutoff: str | None = None):
        if name not in {"pubmed", "dailymed", "faers"}:
            raise ValueError("Unknown source")
        self.name, self.index, self.manifest, self.cutoff = name, index, manifest, cutoff
        if digest(manifest.read_bytes()) != index.corpus.manifest_hash:
            raise IntegrityError("Replay adapter manifest differs from shared index")
        self.documents = {item["doc_id"]: item for item in json.loads(manifest.read_bytes())["documents"]}

    def search(self, action: PlannerDecision, budget: BudgetState) -> SourceSearchResult:
        query = action.query or ""
        fingerprint = query_fingerprint(self.name, query)
        remaining = max(0, budget.max_documents - budget.documents_used)
        documents = []
        seen = set()
        if remaining:
            for hit in self.index.search(
                query, k=len(self.index.corpus.units) or 1, cutoff=self.cutoff, source=self.name
            ):
                unit = hit.unit
                if unit.doc_id in seen:
                    continue
                seen.add(unit.doc_id)
                item = self.documents[unit.doc_id]
                path = (self.manifest.parent / item["path"]).resolve()
                if not path.is_relative_to(self.manifest.parent.resolve()):
                    raise IntegrityError("Replay snapshot leaves corpus directory")
                raw = path.read_bytes()
                if digest(raw) != unit.document_hash:
                    raise IntegrityError("Replay snapshot changed after indexing")
                documents.append(
                    SourceDocument(
                        doc_id=unit.doc_id,
                        source=self.name,
                        source_id=unit.source_id,
                        version=unit.version,
                        title=unit.title,
                        text=raw.decode("utf-8"),
                        hash=unit.document_hash,
                        source_url=item.get("source_url", ""),
                        retrieved_at=item["available_at"],
                        metadata={
                            **item.get("metadata", {}),
                            "mode": "replay",
                            "retrieved_at_kind": "snapshot_available_at",
                            "unit_ids": [row.unit_id for row in self.index.corpus.units if row.doc_id == unit.doc_id],
                        },
                    )
                )
                if len(documents) >= remaining:
                    break
        return SourceSearchResult(
            source=self.name,
            query=query,
            fingerprint=fingerprint,
            status=SourceStatus.OK if documents else SourceStatus.EMPTY,
            documents=documents,
        )
