"""Reproduce an explicitly AI-authored reference; never publish specialist gold."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from eval.corpus import Corpus, IntegrityError, digest, read_jsonl
from eval.person3_dataset import covering_units, export_dataset, write_json, write_rows
from eval.run_evaluation import validate_dataset
from src.services.evidence.corpus import load_candidate_corpus

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "eval/person3/ai-reference-spec.json"


def build_ai_reference(bundle: Path, benchmark: Path, output: Path, *, specification: Path = SPEC):
    spec = json.loads(specification.read_text(encoding="utf-8"))
    if (spec.get("annotator_type") != "ai" or spec.get("annotator_role") != "ai_provisional" or
            spec.get("independent_expert_reviews") != 0 or spec.get("clinical_metrics_ready") is not False or
            spec.get("heldout_exposed_to_annotator") is not True):
        raise IntegrityError("Reference must disclose AI authorship, no expert reviews and heldout exposure")
    if digest((benchmark / "mvp_claims.jsonl").read_bytes()) != spec["claims_sha256"]:
        raise IntegrityError("AI review belongs to different claims; review changed inputs explicitly")
    candidate = load_candidate_corpus(bundle)
    if candidate.bundle_hash != spec["candidate_bundle_sha256"]:
        raise IntegrityError("AI review belongs to a different source bundle")
    docs = {d.doc_id: d for d in candidate.documents}
    anchors = {}
    for family in spec["families"].values():
        for a in family["anchors"]:
            doc = docs[a["doc_id"]]
            start = doc.text.find(a["quote"])
            if start < 0 or doc.text.count(a["quote"]) != 1:
                raise IntegrityError(f"Reference quote must uniquely match exact source: {a['id']}")
            if a["id"] in anchors:
                raise IntegrityError("Duplicate anchor ID")
            if a["route"] == "oral" and "ORAL" not in doc.metadata.get("routes", []):
                raise IntegrityError("Oral route must be backed by pinned source metadata")
            anchors[a["id"]] = {**a, "source": doc.source, "source_url": doc.source_url,
                "source_version": doc.version, "source_sha256": doc.hash,
                "span_locator": {"start": start, "end": start + len(a["quote"]), "unit": "unicode_codepoints"},
                "section_titles": [s["title"] for s in doc.metadata.get("sections", [])
                    if s["start"] < start + len(a["quote"]) and s["end"] > start],
                "route_provenance": {"manifest_metadata_routes": doc.metadata.get("routes", []),
                                     "raw_source_sha256": doc.metadata.get("raw_hash")}}
    export_dataset(bundle, benchmark, output)
    corpus = Corpus.load(output / "corpus_manifest.json")
    claims = read_jsonl(output / "claims.jsonl")
    labels, reviews = [], []
    for c in claims:
        family = spec["families"][c["family_id"]]
        variant = c["claim_id"].rsplit("-", 1)[1]
        decision = spec["variants"][variant]
        selected = [] if variant == "05" else [anchors[a["id"]] for a in family["anchors"]]
        required, relevant, mismatches, reviewed = set(), set(), set(), []
        for anchor in selected:
            span = anchor["span_locator"]
            ids = covering_units(corpus, anchor["doc_id"], span["start"], span["end"])
            relevant.update(ids)
            if anchor["id"] == family["primary_anchor"]:
                required.update(ids)
            fields = [{"field": f, "outcome": "matched", "blocking": False,
                       "reason": "Exact canonical ingredient/event association in quote plus pinned source context."}
                      for f in ("drug", "event")]
            for field in ("population", "dose", "route", "time_window"):
                requested, observed = c.get(field), anchor[field]
                if requested is None and observed is None:
                    outcome, blocking, reason = "unknown", False, "Unspecified in both; no scope value inferred."
                elif requested is not None and requested == observed:
                    outcome, blocking, reason = "matched", False, "Same documented scope value."
                elif field == "route" and requested is not None and observed is not None:
                    outcome, blocking, reason = "mismatched", True, "Requested IV route differs from pinned ORAL label route."
                    mismatches.update(f"{uid}:route" for uid in ids)
                else:
                    outcome, blocking, reason = "unknown", True, (
                        "Requested scope/subgroup is not established by the documented context. "
                        "Do not extrapolate, compare dose strings as disjoint, or substitute follow-up for exposure time.")
                fields.append({"field": field, "requested": requested, "source_scope": observed,
                               "outcome": outcome, "blocking": blocking, "reason": reason})
            reviewed.append({**anchor, "retrieval_unit_ids": ids, "scope_fields": fields,
                             "relevance": "association_context_not_proof_of_full_requested_scope"})
        label = {"claim_id": c["claim_id"], "required_evidence_ids": sorted(required),
                 "relevant_evidence_ids": sorted(relevant), "assessment_status": decision["status"],
                 "abstained": True, "scope_mismatches": sorted(mismatches), "contradictions": [],
                 "annotator_type": "ai", "reference_kind": "ai_provisional", "statement_reviews": []}
        labels.append(label)
        reviews.append({"claim_id": c["claim_id"], "split": c["split"],
                        "assessment_status": decision["status"], "abstained": True,
                        "rationale": decision["reason"] + " " + family["reason"],
                        "evidence_annotations": reviewed, "clinical_approval": False,
                        "contradiction_review": "No direct/apparent pair asserted in selected spans; not an exhaustive negative gold.",
                        "unresolved": ["independent clinical annotation", "statement-level citation entailment",
                                       "exhaustive relevant-unit annotation", "full six-status coverage"]})
    validate_dataset(claims, labels, corpus)
    write_rows(output / "annotations.jsonl", labels)
    write_json(output / "ai-reference-review.json", {"specification": spec, "claims": reviews,
        "document_dispositions": [{"doc_id": d.doc_id, "sha256": d.hash,
            "review_extent": "not_reviewed_reserve_family" if d.doc_id not in {did for c in claims for did in c['related_doc_ids']}
                else "selected_quote_and_context" if any(a["doc_id"] == d.doc_id for a in anchors.values())
                else "abstract_context_screen" if d.source == "pubmed" else "background_or_alternate_label_context",
            "note": spec["document_notes"].get(d.doc_id,
                "Spontaneous reports: co-reported drugs/events, confounding and duplicate/version risks. Not causal or population-rate evidence; not required retrieval reference."
                if d.source == "faers" else "Selected label context/alternate formulation; not an exhaustive clinical review.")}
            for d in candidate.documents]})
    manifest_path = output / "corpus_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance = {k: spec[k] for k in ("annotator_type", "annotator_role", "annotation_date",
        "independent_expert_reviews", "clinical_metrics_ready", "heldout_exposed_to_annotator")}
    provenance.update(specification_sha256=digest(specification.read_bytes()),
                      relevance_inventory="selected_spans_not_exhaustive", citation_entailment="not_measured",
                      contradiction_gold="not_exhaustively_reviewed", heldout_interpretation="family_separated_exposed_technical_set")
    manifest.update(annotation_status="ai_provisional", annotation_provenance=provenance,
                    claims_sha256=digest((output / "claims.jsonl").read_bytes()),
                    annotations_sha256=digest((output / "annotations.jsonl").read_bytes()),
                    ai_review_sha256=digest((output / "ai-reference-review.json").read_bytes()))
    write_json(manifest_path, manifest)
    report = {"annotation_status": "ai_provisional", "claims": len(labels), "exact_quotes": len(anchors),
              "source_documents_with_selected_quotes": len({a['doc_id'] for a in anchors.values()}),
              "retrieval_units": len(corpus.units), "status_counts": dict(Counter(label['assessment_status'] for label in labels)),
              "split_counts": dict(Counter(c['split'] for c in claims)), "provenance": provenance,
              "clinical_metrics_ready": False, "six_status_coverage": False, "live_model_calls": 0,
              "source_http_requests": 0, "corpus_manifest_sha256": digest(manifest_path.read_bytes()),
              "original_expert_files_sha256": {name: digest((benchmark / name).read_bytes())
                  for name in ("reviewer_a.jsonl", "reviewer_b.jsonl", "mvp_gold.jsonl")}}
    write_json(output / "readiness.json", report)
    lines = ["# Nhãn tham chiếu sơ bộ do AI tạo", "",
             "Không có dược sĩ/bác sĩ duyệt; không phải gold chuyên môn. Heldout đã được AI đọc và chỉ còn là tập kiểm tra kỹ thuật tách family.", "",
             "Recall tính trên các đoạn được chọn, không phải toàn bộ bằng chứng liên quan. Không đo độ chính xác lâm sàng hoặc entailment trích dẫn.", ""]
    for row in reviews:
        lines.extend([f"## {row['claim_id']} — {row['assessment_status']}", "", row["rationale"], ""])
        for a in row["evidence_annotations"]:
            lines.extend([f"- {a['doc_id']}, v{a['source_version']}, Unicode {a['span_locator']['start']}:{a['span_locator']['end']}: {a['quote']}",
                          f"  Bối cảnh: {a['scope_basis']}"])
        lines.append("")
    (output / "ai-reference-review.md").write_text("\n".join(lines), encoding="utf-8")
    return report
