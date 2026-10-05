"""Synthetic draft through real Person 2 services + Person 3, without approval or network."""

import argparse
import json
import tempfile
from pathlib import Path

from src.models.schemas import ClaimInput, SourceDocument
from src.services.dossier import render_markdown, validate_dossier
from src.services.evidence.citations import text_hash
from src.services.evidence.integration import configure_person3
from src.services.evidence.nodes import extract_assess_person3
from src.services.llm import LLMGateway, MockProvider
from src.services.runner import RunContext
from src.services.store import MvpStore

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval/person3")
    args = parser.parse_args()
    fixture = json.loads((ROOT / "tests/fixtures/mvp/person3/integration_demo.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="p066-person3-preview-") as folder:
        store = MvpStore(str(Path(folder) / "preview.sqlite3"))
        try:
            state, _ = store.create_investigation(ClaimInput(**fixture["claim"]))
            ctx = configure_person3(
                RunContext(store=store, gateway=LLMGateway(MockProvider({"extract_evidence": fixture["response"]}))),
                ROOT / "data/dictionaries/person3_synthetic.json", allow_synthetic=True,
            )
            normalized = ctx.normalizer.normalize_claim(state.claim)
            doc = SourceDocument(**fixture["document"], hash=text_hash(fixture["document"]["text"]))
            store.save_document(state.investigation_id, doc)
            state = store.save_state(state.model_copy(update={"documents": [doc], "normalized_claim": normalized,
                                                              "searched_sources": [doc.source]}))
            state = extract_assess_person3({"investigation": state, "ctx": ctx})["investigation"]
            dossier = ctx.dossier_builder(state)
            validation = validate_dossier(dossier, state)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            label = "> SYNTHETIC TECHNICAL DRAFT. Not clinical evidence, not approved, not official export.\n\n"
            (args.output_dir / "dossier-integration-draft.md").write_text(label + render_markdown(dossier), encoding="utf-8")
            (args.output_dir / "integration-preview.json").write_text(json.dumps({
                "mode": "synthetic", "approved": False, "official_export": False,
                "assessment_status": state.assessment_status, "budget": state.budget.model_dump(),
                "validation": validation.model_dump(), "clinical_metrics": None,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Synthetic integration preview: citation checks={'passed' if validation.ok else 'failed'}, approved=False")
        finally:
            store.close()


if __name__ == "__main__":
    main()
