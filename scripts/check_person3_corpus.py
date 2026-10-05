"""Run Person 3 extraction/citation/dossier checks on real frozen source documents."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))


def main():
    from src.models.schemas import BudgetState, ClaimInput, InvestigationState, EvidenceGap, GapKind
    from src.services.evidence.corpus import load_candidate_corpus
    from src.services.evidence.corpus_runtime import DEFAULT_BUNDLE, DEFAULT_DICTIONARY
    from src.services.evidence.normalize import ClaimNormalizer
    from src.services.evidence.candidate_provider import CandidateQuoteProvider
    from src.services.evidence.extract import EvidenceExtractor
    from src.services.evidence.citations import validate_evidence_citation
    from src.services.evidence.contracts import read_annotation
    from src.services.evidence.analysis import EvidenceAnalyzer
    from src.services.evidence.dossier import build_person3_dossier
    from src.services.dossier import render_markdown, validate_dossier
    from src.services.llm import LLMGateway, TransportProvider
    from src.services.errors import MvpError
    from src.services.evidence.check_report import summarize_checks

    class RecordingTransport:
        name = "recorded-transport"

        def __init__(self):
            self.inner = TransportProvider()
            self.outputs = []

        def complete(self, **kwargs):
            response = self.inner.complete(**kwargs)
            self.outputs.append({"task": kwargs["task"], "model": response.model, "text": response.text})
            return response

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", default="metformin", choices=["metformin", "ibuprofen", "lisinopril", "atorvastatin", "amoxicillin", "all"])
    parser.add_argument("--provider", choices=["offline", "transport"], default="offline")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--doc-id", help="Check just one document before a full live run")
    parser.add_argument("--summary", action="store_true", help="Summarize saved results without model calls")
    args = parser.parse_args()
    folder = ROOT / "eval/person3/corpus" / args.provider
    suffix = "-single-document" if args.doc_id else ""
    report_path = folder / f"report-{args.family}{suffix}.json"
    if args.summary:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        summary = summarize_checks(report["results"])
        print(f"Saved results: {summary['documents_checked']} documents; valid quotes={summary['valid_quotes']}; excluded quotes={summary['excluded_quotes']}")
        print(f"Processing failures={len(summary['processing_failures'])}; documents needing quote review={len(summary['documents_with_excluded_quotes'])}")
        print("No model calls made. Clinical gold/accuracy/entailment: not measured.")
        return bool(summary["processing_failures"])
    corpus = load_candidate_corpus(args.bundle)
    normalizer = ClaimNormalizer(DEFAULT_DICTIONARY)
    if normalizer.dictionary.get("corpus_sha256") != corpus.bundle_hash:
        raise ValueError("Prepare the dictionary for this corpus first")
    results = []
    folder.mkdir(parents=True, exist_ok=True)
    for pair in corpus.collection["pairs"]:
        if args.family != "all" and pair["drug"] != args.family:
            continue
        claim = ClaimInput(claim_text=f"Investigate reported association: {pair['drug']} / {pair['event']}",
                           drug=pair["drug"], event=pair["event"])
        normalized = normalizer.normalize_claim(claim)
        for doc in corpus.documents_for(pair["drug"]):
            if args.doc_id and doc.doc_id != args.doc_id:
                continue
            provider = CandidateQuoteProvider(normalizer.dictionary) if args.provider == "offline" else RecordingTransport()
            gateway = LLMGateway(provider)
            extractor = EvidenceExtractor(gateway, dictionary=normalizer.dictionary)
            budget = BudgetState()
            inv_id = "CHECK-" + doc.doc_id.replace(":", "-")
            extractor.bind(budget, inv_id)
            error = None
            try:
                units = extractor.extract_evidence(doc, normalized)
            except MvpError as e:
                units = extractor.partial_units.get(doc.doc_id, [])
                error = str(e.code)
            checks = [validate_evidence_citation(doc, item) for item in units if not item.excluded]
            analysis = EvidenceAnalyzer().analyze(units, normalized)
            gaps = list(analysis.gaps)
            coverage = extractor.coverage.get(doc.doc_id, {})
            if not coverage.get("complete"):
                gaps.append(EvidenceGap(gap_id="GAP-P3-COVERAGE", kind=GapKind.MISSING_EVIDENCE, field="document",
                    description=f"Examined {coverage.get('examined_chars', 0)}/{len(doc.text)} characters; source coverage is partial."))
            state = InvestigationState(investigation_id=inv_id, claim=claim, normalized_claim=normalized,
                documents=[doc], evidence=units, budget=budget, assessment=analysis.assessment,
                assessment_status=analysis.assessment.assessment_status, gaps=gaps)
            dossier = build_person3_dossier(state)
            dossier_check = validate_dossier(dossier, state)
            result = {"doc_id": doc.doc_id, "source": doc.source, "source_url": doc.source_url,
                "document_hash": doc.hash, "family": pair["drug"], "provider": args.provider,
                "clinical_gold": False, "error": error, "coverage": extractor.coverage.get(doc.doc_id),
                "evidence": [u.model_dump(mode="json") for u in units],
                "valid_quotes": len(checks), "excluded_quotes": sum(u.excluded for u in units),
                "citation_errors": [e for c in checks for e in c.errors],
                "exclusion_reasons": dict(Counter(issue for u in units if u.excluded
                    for issue in (read_annotation(u.notes).issues if read_annotation(u.notes) else ["missing_annotation"]))),
                "alignment_events": extractor.alignment_events,
                "raw_model_outputs": provider.outputs if args.provider == "transport" else [],
                "assessment_status": str(state.assessment_status), "dossier_errors": dossier_check.errors,
                "model_responses_received": len(gateway.ledger.records) if args.provider == "transport" else 0,
                "gateway_usage": gateway.ledger.model_dump(), "budget_scope": "per_document_check_not_full_investigation"}
            name = inv_id
            (folder / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            preview = "# UNAPPROVED SOURCE CHECK — NOT CLINICAL GOLD\n\n"
            preview += "Sources are real; offline mode proposes lexical quotes only. Missing context stays unknown.\n\n"
            preview += f"Coverage: {json.dumps(result['coverage'])}\n\n" + render_markdown(dossier)
            (folder / f"{name}.md").write_text(preview, encoding="utf-8")
            results.append({k: v for k, v in result.items() if k not in {"evidence", "gateway_usage", "alignment_events", "raw_model_outputs"}})
    if not results:
        raise ValueError("No documents selected; verify --family/--doc-id")
    report = {"sources": "real_frozen_candidates", "provider": args.provider, "family": args.family,
        "bundle_sha256": corpus.bundle_hash, "live_search": False, "clinical_metrics_measured": False,
        "live_provider_requested": args.provider == "transport",
        "actual_model_responses_received": sum(r["model_responses_received"] for r in results),
        "gateway_usage_is_simulated": args.provider == "offline",
        **summarize_checks(results),
        "extraction_errors": dict(Counter(r["error"] for r in results if r["error"])),
        "results": results}
    # Compatibility field: failures now means processing/validation failures;
    # excluded model quotes are explicitly reported for human review.
    report["failures"] = report["processing_failures"]
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REAL sources / {args.provider}: {len(results)} documents, {report['valid_quotes']} valid candidate quotes; processing failures={len(report['processing_failures'])}")
    print(f"Excluded quotes={report['excluded_quotes']}; extraction errors={report['extraction_errors']}")
    print(f"Documents needing quote review={len(report['documents_with_excluded_quotes'])}")
    print("Clinical gold/accuracy/entailment: not measured. Previews are unapproved.")
    return bool(report["processing_failures"])


if __name__ == "__main__":
    raise SystemExit(main())
