"""Bind Person 3 modules to Person 2's RunContext."""

from pathlib import Path

from src.services.evidence.analysis import EvidenceAnalyzer
from src.services.evidence.extract import EvidenceExtractor
from src.services.evidence.normalize import ClaimNormalizer


def configure_person3(ctx, dictionary_path: str | Path, *, allow_synthetic: bool = False):
    """Call on each context returned by the runner, before run_investigation.

    No replacement source adapters: Person 1 owns ctx.adapters.
    The merged graph binds the extraction budget and uses ctx.evidence_analyzer.
    """
    from src.services.evidence.dossier import build_person3_dossier

    ctx.normalizer = ClaimNormalizer(dictionary_path, allow_synthetic=allow_synthetic)
    ctx.extractor = EvidenceExtractor(ctx.gateway, dictionary=ctx.normalizer.dictionary)
    ctx.evidence_analyzer = EvidenceAnalyzer()
    ctx.dossier_builder = build_person3_dossier
    return ctx


def make_person3_executor(dictionary_path: str | Path, *, allow_synthetic: bool = False):
    """Supply as InProcessRunner(executor=...) so every run/resume gets the bindings."""
    # Reject a missing, malformed or synthetic dictionary before opening the API
    # store or accepting an investigation. Each context still gets a fresh extractor.
    ClaimNormalizer(dictionary_path, allow_synthetic=allow_synthetic)

    def execute(state, ctx):
        from src.agents.graph import run_investigation

        configure_person3(ctx, dictionary_path, allow_synthetic=allow_synthetic)
        return run_investigation(state, ctx)

    return execute
