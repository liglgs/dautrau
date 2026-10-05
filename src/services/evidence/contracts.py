"""Person 3 structured extraction; public inputs/outputs remain Person 2 models."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.models.schemas import EvidenceScope, EvidenceType, QuoteLocator, Stance


class EvidenceAnnotation(BaseModel):
    """Versioned context stored in EvidenceUnit.notes until the shared model expands.

    These are extracted observations, not adjudicated gold labels. Free-text notes
    from other producers never establish a drug/event match or precision.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["person3.1"] = "person3.1"
    drug_ingredient: str | None = Field(default=None, max_length=200)
    event_term: str | None = Field(default=None, max_length=200)
    comparator: str | None = Field(default=None, max_length=120)
    direction: Literal["increase", "decrease", "no_clear_effect", "unknown"] = "unknown"
    uncertainty: Literal["low", "high", "unknown"] = "unknown"
    document_version: int = Field(ge=1)
    document_hash: str = Field(min_length=8, max_length=128)
    issues: list[str] = Field(default_factory=list, max_length=12)

    def to_notes(self) -> str:
        encoded = self.model_dump_json(exclude_none=True)
        if len(encoded) > 1000:
            raise ValueError("Extraction context exceeds EvidenceUnit.notes; do not truncate JSON")
        return encoded


def read_annotation(notes: str) -> EvidenceAnnotation | None:
    try:
        return EvidenceAnnotation.model_validate(json.loads(notes))
    except (ValueError, TypeError):
        return None


class ExtractedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1, max_length=2000)
    # Models can quote accurately but cannot reliably count character offsets.
    # The extractor resolves a missing/wrong locator only for an exact unique
    # quote in the examined window; the public EvidenceUnit still requires one.
    locator: QuoteLocator | None = None
    scope: EvidenceScope = Field(default_factory=EvidenceScope)
    drug_ingredient: str | None = Field(default=None, max_length=200)
    event_term: str | None = Field(default=None, max_length=200)
    comparator: str | None = Field(default=None, max_length=120)
    stance: Stance = Stance.UNCERTAIN
    direction: Literal["increase", "decrease", "no_clear_effect", "unknown"] = "unknown"
    uncertainty: Literal["low", "high", "unknown"] = "unknown"
    evidence_type: EvidenceType = EvidenceType.OTHER


class ExtractionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[ExtractedFinding] = Field(max_length=20)
