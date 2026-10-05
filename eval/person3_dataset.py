"""Export candidate snapshots to the common evaluation contract without inventing gold."""

from __future__ import annotations

import json
from pathlib import Path

from eval.corpus import Corpus, IntegrityError, digest, read_jsonl, timestamp
from eval.run_evaluation import validate_dataset
from src.services.evidence.annotation_review import compare_reviews, validate_annotation
from src.services.evidence.corpus import load_candidate_corpus

ROOT = Path(__file__).resolve().parents[1]
UNIT_VERSION = "unicode-fixed-2000-v1"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_rows(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def covering_units(corpus, doc_id, start, end):
    """Map a checked quote to every fixed retrieval unit it overlaps, in source order."""
    units = [u for u in corpus.units if u.doc_id == doc_id and u.start < end and u.end > start]
    if not units or units[0].start > start or units[-1].end < end:
        raise IntegrityError("Annotated span is outside the common retrieval index")
    if any(a.end != b.start for a, b in zip(units, units[1:])):
        raise IntegrityError("Retrieval units do not cover the annotated span")
    return [u.unit_id for u in units]


def convert_annotation(row, corpus):
    refs = {}
    mismatch = set()
    fields = {"drug_ingredient": "drug", "event_term": "event"}
    for item in row["evidence_annotations"]:
        span = item["span_locator"]
        ids = covering_units(corpus, item["document_id"], span["start"], span["end"])
        refs[item["evidence_id"]] = ids
        for comparison in item.get("scope_fields", []):
            if comparison.get("outcome") == "mismatched":
                field = fields.get(comparison["field"], comparison["field"])
                mismatch.update(f"{uid}:{field}" for uid in ids)
    contradictions = set()
    for pair in row.get("contradiction_annotations", []):
        kind = pair["kind"]
        if kind not in {"direct", "apparent"}:
            continue
        left, right = pair["evidence_ids"]
        for a in refs[left]:
            for b in refs[right]:
                if a == b:
                    raise IntegrityError("Opposing spans share a retrieval unit; refine the index before freezing")
                contradictions.add(f"{kind}:{min(a, b)}|{max(a, b)}")
    required = {uid for eid in row["required_gold_evidence_ids"] for uid in refs[eid]}
    relevant = required | {uid for eid in row["optional_gold_evidence_ids"] for uid in refs[eid]}
    return {
        "claim_id": row["claim_id"], "required_evidence_ids": sorted(required),
        "relevant_evidence_ids": sorted(relevant), "assessment_status": row["expected_assessment_status"],
        "abstained": row["expected_abstention"], "scope_mismatches": sorted(mismatch),
        "contradictions": sorted(contradictions),
    }


def export_dataset(bundle: Path, benchmark: Path, output: Path, *, approval: Path | None = None):
    candidate = load_candidate_corpus(bundle)
    proposal = json.loads((benchmark / "mvp_manifest.json").read_text(encoding="utf-8"))
    original = read_jsonl(benchmark / "mvp_claims.jsonl")
    if proposal["corpus_sha256"] != candidate.bundle_hash:
        raise IntegrityError("Proposed split belongs to another candidate bundle")
    proposed_cutoff = proposal["corpus_cutoff"]
    # collection.created_at marks collection START, not the last available snapshot.
    cutoff = max(timestamp(proposed_cutoff), *(d.retrieved_at for d in candidate.documents)).isoformat()
    dictionary = ROOT / "data/dictionaries/mvp_candidates_2026_10_02.json"
    dictionary_data = json.loads(dictionary.read_text(encoding="utf-8"))
    if dictionary_data.get("corpus_sha256") != candidate.bundle_hash:
        raise IntegrityError("Dictionary belongs to another candidate bundle")
    documents = []
    snapshots = {}
    for doc in candidate.documents:
        available = doc.retrieved_at.isoformat()
        if timestamp(available) > timestamp(cutoff):
            raise IntegrityError("Snapshot was collected after the proposed cutoff")
        path = f"snapshots/{digest(doc.doc_id.encode())[:24]}.txt"
        snapshots[path] = doc.text
        units = [{"unit_id": "P3U-" + digest(f"{doc.doc_id}|{doc.hash}|{a}|{min(a+2000,len(doc.text))}|{UNIT_VERSION}".encode())[:24],
                  "start": a, "end": min(a + 2000, len(doc.text)), "text": doc.text[a:a+2000]}
                 for a in range(0, len(doc.text), 2000)]
        documents.append({"doc_id": doc.doc_id, "source": doc.source, "source_id": doc.source_id,
                          "version": doc.version, "title": doc.title, "path": path,
                          "sha256": doc.hash, "available_at": available, "source_url": doc.source_url,
                          "metadata": doc.metadata, "units": units})
    claims = [{"claim_id": c["claim_id"], "family_id": c["family_id"], "split": c["split"],
               **c["claim"], "cutoff": cutoff, "related_doc_ids": c["source_doc_ids"]} for c in original]
    # Validate family/document separation before asking anyone to annotate.
    families, identities, seen = {}, {}, set()
    docs = {d["doc_id"]: d for d in documents}
    for c in claims:
        if c["claim_id"] in seen or c["split"] not in {"development", "heldout"}:
            raise IntegrityError("Duplicate claim or invalid split")
        seen.add(c["claim_id"])
        if families.setdefault(c["family_id"], c["split"]) != c["split"]:
            raise IntegrityError("Family overlaps evaluation splits")
        for did in c["related_doc_ids"]:
            d = docs[did]
            if identities.setdefault((d["source"], d["source_id"]), c["split"]) != c["split"]:
                raise IntegrityError("Source identity overlaps evaluation splits")
    if output.exists():
        raise FileExistsError("Output already exists; choose a new folder to preserve review work")
    output.mkdir(parents=True)
    for relative, content in snapshots.items():
        target = output / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(content.encode("utf-8"))
    manifest = {"schema_version": 1, "mode": "replay", "synthetic": False,
                "annotation_status": "pending_independent_review", "cutoff": cutoff,
                "cutoff_kind": "last_snapshot_available_at", "proposed_collection_start": proposed_cutoff,
                "versions": {"dictionary": dictionary_data["version"], "dictionary_sha256": digest(dictionary.read_bytes()),
                             "parser": "candidate-bundle-parsed-text-v1", "units": UNIT_VERSION,
                             "policy": "person3-conservative-v1"},
                "candidate_bundle_sha256": candidate.bundle_hash, "documents": documents}
    write_json(output / "corpus_manifest.json", manifest)
    write_rows(output / "claims.jsonl", claims)
    corpus = Corpus.load(output / "corpus_manifest.json")
    templates = [{"claim_id": c["claim_id"], "required_evidence_ids": [], "relevant_evidence_ids": [],
                  "assessment_status": None, "abstained": None,
                  "scope_mismatches": [], "contradictions": []} for c in claims]
    write_rows(output / "annotations.template.jsonl", templates)
    # Each expert receives the original structured form, with the same immutable sources.
    for slot in ("reviewer_a", "reviewer_b"):
        write_rows(output / f"{slot}.jsonl", read_jsonl(benchmark / f"{slot}.jsonl"))
    write_rows(output / "mvp_claims.jsonl", original)
    write_json(output / "mvp_manifest.json", proposal)
    write_json(output / "freeze_approval.template.json", {
        "adjudicator_id": None, "adjudicator_role": None, "approved_at": None, "reason": None,
        "candidate_bundle_sha256": candidate.bundle_hash,
        "retrieval_manifest_sha256": digest((output / "corpus_manifest.json").read_bytes()),
        "evaluation_cutoff": cutoff,
        "input_sha256": {name: digest((benchmark / name).read_bytes()) for name in
                         ("mvp_manifest.json", "mvp_claims.jsonl", "reviewer_a.jsonl", "reviewer_b.jsonl")},
        "final_annotations": [],
        "instructions": "Update hashes after both reviews. A specialist explicitly resolves all 20 final annotations; do not fabricate labels."})
    ready = False
    if approval:
        decision = json.loads(approval.read_text(encoding="utf-8"))
        reviews = [read_jsonl(benchmark / f"{slot}.jsonl") for slot in ("reviewer_a", "reviewer_b")]
        checked = compare_reviews(original, *reviews, candidate)
        if checked["pending"]:
            raise IntegrityError("Both independent specialist reviews must be complete and valid")
        for name in ("adjudicator_id", "adjudicator_role", "approved_at", "reason"):
            if not decision.get(name):
                raise IntegrityError(f"Freeze approval requires {name}")
        if decision["adjudicator_role"] not in {"clinical_pharmacist", "physician", "pharmacovigilance_specialist"}:
            raise IntegrityError("Specialist adjudicator role required")
        timestamp(decision["approved_at"])
        hashes = {name: digest((benchmark / name).read_bytes()) for name in
                  ("mvp_manifest.json", "mvp_claims.jsonl", "reviewer_a.jsonl", "reviewer_b.jsonl")}
        if decision.get("input_sha256") != hashes or decision.get("candidate_bundle_sha256") != candidate.bundle_hash:
            raise IntegrityError("Freeze approval does not pin all reviewed inputs")
        if (decision.get("retrieval_manifest_sha256") != digest((output / "corpus_manifest.json").read_bytes()) or
                decision.get("evaluation_cutoff") != cutoff):
            raise IntegrityError("Freeze approval must pin the reviewed retrieval units and snapshot cutoff")
        finals = decision.get("final_annotations", [])
        if len(finals) != len(original) or {r["claim_id"] for r in finals} != seen:
            raise IntegrityError("Adjudicator must explicitly resolve every claim")
        annotations = []
        by_id = {c["claim_id"]: c for c in original}
        for row in finals:
            errors = validate_annotation(row, by_id[row["claim_id"]], candidate)
            if errors:
                raise IntegrityError("Invalid adjudication: " + "; ".join(errors))
            adjudication = row.get("adjudication", {})
            if (adjudication.get("status") != "resolved" or
                    adjudication.get("adjudicator_id") != decision["adjudicator_id"] or
                    not adjudication.get("resolution_reason")):
                raise IntegrityError("Every final label needs a signed resolution reason")
            annotations.append(convert_annotation(row, corpus))
        validate_dataset(claims, annotations, corpus)
        write_rows(output / "annotations.jsonl", annotations)
        write_json(output / "freeze_approval.json", decision)
        manifest["annotation_status"] = "independently_reviewed"
        manifest["freeze_approval_sha256"] = digest(approval.read_bytes())
        write_json(output / "corpus_manifest.json", manifest)
        ready = True
    report = {"documents": len(documents), "retrieval_units": len(corpus.units), "claims": len(claims),
              "split_counts": {s: sum(c["split"] == s for c in claims) for s in ("development", "heldout")},
              "clinical_metrics_ready": ready, "synthetic": False, "unit_policy": UNIT_VERSION,
              "labels_generated_by_model": False, "corpus_manifest_sha256": digest((output / "corpus_manifest.json").read_bytes())}
    write_json(output / "readiness.json", report)
    return report
