"""Structured extraction through the budgeted gateway, with strict source spans."""

from __future__ import annotations

from hashlib import sha256

from src.models.schemas import (
    BudgetState,
    EvidenceType,
    EvidenceUnit,
    NormalizedClaim,
    QuoteLocator,
    SourceDocument,
    Stance,
)
from src.services.evidence.chunks import coverage_summary, document_windows
from src.services.evidence.citations import text_hash, validate_evidence_citation
from src.services.evidence.contracts import EvidenceAnnotation, ExtractionBatch
from src.services.prompts import UntrustedChunk


def align_quote(window, quote, locator):
    """Return a source span, never edit a quotation or search unexamined text."""
    if locator is not None and locator.end <= len(window.text) and window.text[locator.start:locator.end] == quote:
        return locator, "as_reported"
    start = window.text.find(quote)
    if start >= 0 and window.text.find(quote, start + 1) < 0:
        return QuoteLocator(start=start, end=start + len(quote)), "realigned_exact_unique"
    fallback = locator or QuoteLocator(start=0, end=len(quote))
    return fallback, "ambiguous_quote_locator" if start >= 0 else "quote_not_in_examined_window"


class EvidenceExtractor:
    """Synchronous Person 2 protocol. Budget must be bound before extraction.

    A run-local cache avoids extracting unchanged documents at every graph step;
    it never crosses investigations or changed claim/document versions.
    """

    def __init__(self, gateway, *, dictionary: dict | None = None, max_windows: int = 3):
        self.gateway = gateway
        self.dictionary = dictionary
        self.budget: BudgetState | None = None
        self.investigation_id: str | None = None
        self._cache: dict[tuple, list[EvidenceUnit]] = {}
        self.warnings: list[str] = []
        self.max_windows = max_windows
        self.coverage: dict[str, dict] = {}
        self.partial_units: dict[str, list[EvidenceUnit]] = {}
        self.alignment_events: list[dict] = []

    def bind(self, budget: BudgetState, investigation_id: str) -> None:
        if self.investigation_id != investigation_id:
            self._cache.clear()
            self.warnings.clear()
            self.coverage.clear()
            self.partial_units.clear()
            self.alignment_events.clear()
        self.budget = budget
        self.investigation_id = investigation_id

    def extract_evidence(self, document: SourceDocument, claim: NormalizedClaim) -> list[EvidenceUnit]:
        if self.budget is None or self.investigation_id is None:
            raise RuntimeError("Bind the run budget before calling extraction")
        if document.hash != text_hash(document.text):
            raise ValueError(f"Document hash mismatch: {document.doc_id}")
        windows = document_windows(document, claim, self.dictionary, max_windows=self.max_windows)
        examined, result, seen = [], [], set()
        self.partial_units[document.doc_id] = []
        self.coverage[document.doc_id] = coverage_summary([], len(document.text))
        for window in windows:
            units = self._extract_window(document, claim, window)
            examined.append(window)
            for unit in units:
                if unit.evidence_id not in seen:
                    result.append(unit)
                    seen.add(unit.evidence_id)
            self.partial_units[document.doc_id] = [u.model_copy(deep=True) for u in result]
            self.coverage[document.doc_id] = coverage_summary(examined, len(document.text))
        if not self.coverage[document.doc_id]["complete"]:
            self.warnings.append(f"{document.doc_id}: selected windows examined; document coverage is partial")
        return result

    def _extract_window(self, document, claim, window):
        key = (document.doc_id, document.version, document.hash, claim.model_dump_json(), window.start, window.end)
        if key in self._cache:
            return [item.model_copy(deep=True) for item in self._cache[key]]

        batch = self.gateway.invoke(
            "extract_evidence",
            {
                "claim": claim.model_dump(),
                "document": {"doc_id": document.doc_id, "source": document.source, "version": document.version,
                             "window_start": window.start, "window_end": window.end,
                             "locator_unit": "unicode_code_points_relative_to_window",
                             "response_schema": ExtractionBatch.model_json_schema()},
            },
            ExtractionBatch,
            budget=self.budget,
            untrusted=[UntrustedChunk(
                text=window.text, source=document.source, source_id=document.source_id,
            )],
            context={"investigation_id": self.investigation_id, "doc_id": document.doc_id},
        )
        result = []
        seen = set()
        for finding in batch.findings:
            reported = finding.locator
            locator, alignment = align_quote(window, finding.quote, reported)
            alignment_failed = alignment in {"ambiguous_quote_locator", "quote_not_in_examined_window"}
            outside = locator.end > len(window.text)
            finding = finding.model_copy(update={"locator": locator.model_copy(update={
                "start": locator.start + window.start, "end": locator.end + window.start,
            })})
            identity = (finding.locator.start, finding.locator.end, finding.quote)
            if identity in seen:
                continue
            seen.add(identity)
            issues = ["document_partially_examined"] if len(document.text) > len(window.text) else []
            if alignment != "as_reported":
                issues.append(alignment)
                self.alignment_events.append({"doc_id": document.doc_id, "document_hash": document.hash,
                    "window_start": window.start, "window_end": window.end,
                    "model_locator": reported.model_dump() if reported is not None else None,
                    "resolved_locator": finding.locator.model_dump(), "status": alignment})
            targets = {"drug_ingredient": finding.drug_ingredient, "event_term": finding.event_term}
            if self.dictionary:
                for name, section in (("drug_ingredient", "drugs"), ("event_term", "events")):
                    term = targets[name]
                    if term is None:
                        continue
                    term_key = " ".join(term.casefold().split())
                    candidates = {record["canonical"] for record in self.dictionary[section]
                                  if term_key in {" ".join(alias.casefold().split())
                                             for alias in [record["canonical"], *record["aliases"]]}}
                    targets[name] = next(iter(candidates)) if len(candidates) == 1 else None
                    if targets[name] is None:
                        issues.append(f"unresolved_{name}")
            stance = finding.stance
            if document.source == "faers":
                stance = Stance.UNCERTAIN
                evidence_type = EvidenceType.FAERS_REPORT
                issues.append("faers_background_only")
            else:
                evidence_type = finding.evidence_type
                if finding.uncertainty != "low" or finding.direction in {"unknown", "no_clear_effect"}:
                    stance = Stance.UNCERTAIN
                    issues.append("uncertain_result")
                if ((stance is Stance.SUPPORTS and finding.direction != "increase")
                        or (stance is Stance.CONTRADICTS and finding.direction != "decrease")):
                    stance = Stance.UNCERTAIN
                    issues.append("inconsistent_direction")
            if outside:
                issues.append("outside_examined_text")
                self.warnings.append(f"{document.doc_id}: finding locator is outside its examined window")
            annotation = EvidenceAnnotation(
                **targets,
                comparator=finding.comparator, direction=finding.direction, uncertainty=finding.uncertainty,
                document_version=document.version, document_hash=document.hash, issues=issues,
            )
            digest = sha256(
                f"{document.doc_id}|{document.version}|{identity}".encode()
            ).hexdigest()[:24]
            unit = EvidenceUnit(
                evidence_id=f"EV-P3-{digest}", doc_id=document.doc_id, source=document.source,
                stance=stance, quote=finding.quote, locator=finding.locator, scope=finding.scope,
                evidence_type=evidence_type, confidence=0.0, notes=annotation.to_notes(),
            )
            checked = validate_evidence_citation(document, unit)
            if checked.errors or "outside_examined_text" in issues or alignment_failed:
                annotation.issues.extend(checked.errors)
                unit = unit.model_copy(update={"excluded": True, "notes": annotation.to_notes()})
            result.append(unit)
        self._cache[key] = [item.model_copy(deep=True) for item in result]
        return result
