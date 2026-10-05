"""Exact dictionary lookup before the structured LLM gateway is available."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NormalizationDraft:
    original_drug: str
    original_event: str
    ingredient_candidates: tuple[str, ...]
    event_candidates: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    ambiguities: tuple[str, ...]
    dictionary_version: str
    requires_review: bool
    mode: str


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


def load_dictionary(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("mode") not in {"synthetic", "verified"} or not payload.get("version"):
        raise ValueError("Dictionary needs a mode and version")
    for section in ("drugs", "events"):
        records = payload.get(section)
        if not isinstance(records, list) or not records:
            raise ValueError(f"Dictionary needs {section} records")
        for record in records:
            if not record.get("canonical") or not record.get("source_ref") or not record.get("license"):
                raise ValueError("Each mapping needs canonical term, provenance and permission")
            if not isinstance(record.get("aliases"), list) or not all(
                isinstance(alias, str) and alias.strip() for alias in record["aliases"]
            ):
                raise ValueError("Aliases must be a list of nonblank strings")
    return payload


def normalize_claim(drug: str, event: str, dictionary: dict, *, allow_synthetic: bool = False) -> NormalizationDraft:
    """Return candidates only; never guess an ingredient or event code."""
    if not isinstance(drug, str) or not drug.strip() or not isinstance(event, str) or not event.strip():
        raise ValueError("Drug and event are required")
    if dictionary["mode"] == "synthetic" and not allow_synthetic:
        raise ValueError("Synthetic dictionary requires explicit offline opt-in")

    def candidates(section: str, term: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    record["canonical"]
                    for record in dictionary[section]
                    if _key(term) in {_key(alias) for alias in [record["canonical"], *record["aliases"]]}
                }
            )
        )

    ingredients, events = candidates("drugs", drug), candidates("events", event)
    unknowns = tuple(name for name, values in (("ingredient", ingredients), ("event", events)) if not values)
    ambiguities = tuple(name for name, values in (("ingredient", ingredients), ("event", events)) if len(values) > 1)
    return NormalizationDraft(
        drug, event, ingredients, events, unknowns, ambiguities, dictionary["version"],
        bool(unknowns or ambiguities), dictionary["mode"],
    )


class ClaimNormalizer:
    """Adapter for Person 2's normalize_claim(ClaimInput) protocol."""

    def __init__(self, dictionary_path: str | Path, *, allow_synthetic: bool = False):
        self.dictionary = load_dictionary(dictionary_path)
        self.allow_synthetic = allow_synthetic
        if self.dictionary["mode"] == "synthetic" and not allow_synthetic:
            raise ValueError("Synthetic dictionary requires explicit offline opt-in")

    def normalize_claim(self, claim):
        from src.models.schemas import ClaimInput, NormalizedClaim

        claim = ClaimInput.model_validate(claim)
        result = normalize_claim(
            claim.drug, claim.event, self.dictionary, allow_synthetic=self.allow_synthetic
        )
        # Public schema requires strings: retain the user's unresolved term, flag
        # review, and never pick the first ingredient from an ambiguous brand.
        ingredient = result.ingredient_candidates[0] if len(result.ingredient_candidates) == 1 else claim.drug
        event = result.event_candidates[0] if len(result.event_candidates) == 1 else claim.event
        synonyms = sorted({
            alias for record in self.dictionary["drugs"] if record["canonical"] == ingredient
            for alias in record["aliases"]
        })
        fields = {name: getattr(claim, name) for name in ("population", "dose", "route", "time_window")}
        unknowns = [{"ingredient": "drug_ingredient", "event": "event_term"}[name] for name in result.unknown_fields]
        unknowns.extend(name for name, value in fields.items() if not value or not value.strip())
        ambiguities = [
            f"{name}: {', '.join(result.ingredient_candidates if name == 'ingredient' else result.event_candidates)}"
            for name in result.ambiguities
        ]
        return NormalizedClaim(
            claim_text=claim.claim_text, drug_ingredient=ingredient, drug_synonyms=synonyms,
            event_term=event, **fields, unknowns=unknowns, ambiguities=ambiguities,
            requires_review=result.requires_review,
        )
