"""Check independent expert review packets; never invent or autofill gold labels."""

from collections import Counter
from datetime import datetime

from src.models.schemas import AssessmentStatus

LABELS = {status.value for status in AssessmentStatus}
EXPERT_ROLES = {"clinical_pharmacist", "physician", "pharmacovigilance_specialist"}


def validate_annotation(row, claim, corpus):
    errors = []
    for field, expected in (("claim_id", claim["claim_id"]), ("claim_version", claim["version"]),
                            ("family_id", claim["family_id"]), ("split", claim["split"]),
                            ("source_manifest_sha256", corpus.bundle_hash)):
        if row.get(field) != expected:
            errors.append(f"{field}: stale or mismatched")
    if row.get("record_status") != "completed_independent_expert_review":
        errors.append("Independent expert review is pending")
    if not row.get("annotator_id") or not row.get("annotation_timestamp"):
        errors.append("Annotator identity/timestamp required")
    else:
        try:
            if datetime.fromisoformat(row["annotation_timestamp"].replace("Z", "+00:00")).tzinfo is None:
                errors.append("Annotation timestamp needs timezone")
        except (AttributeError, TypeError, ValueError):
            errors.append("Invalid annotation timestamp")
    if row.get("annotator_role") not in EXPERT_ROLES:
        errors.append("Declared specialist role required; credentials must be checked by the team")
    if row.get("expected_assessment_status") not in LABELS:
        errors.append("Expected assessment label is missing or invalid")
    if row.get("expected_abstention") not in {True, False} or not isinstance(row.get("expected_abstention"), bool):
        errors.append("Expected abstention must be a boolean")
    documents = {d.doc_id: d for d in corpus.documents}
    annotations = row.get("evidence_annotations", [])
    ids = set()
    for annotation in annotations:
        eid = annotation.get("evidence_id")
        if not eid or eid in ids:
            errors.append("Evidence IDs must be nonblank and unique")
        ids.add(eid)
        doc_id = annotation.get("document_id")
        doc = documents.get(doc_id)
        if doc is None or doc_id not in claim["source_doc_ids"]:
            errors.append(f"{eid}: document outside claim corpus")
            continue
        if annotation.get("source_id") != doc.source_id or annotation.get("source_version") != doc.version or annotation.get("parsed_text_hash") != doc.hash:
            errors.append(f"{eid}: stale source identity/version/hash")
        locator = annotation.get("span_locator", {})
        a, b = locator.get("start"), locator.get("end")
        if locator.get("unit") != "unicode_code_points" or type(a) is not int or type(b) is not int or not 0 <= a < b <= len(doc.text):
            errors.append(f"{eid}: invalid span locator")
        elif doc.text[a:b] != annotation.get("quoted_span"):
            errors.append(f"{eid}: quotation does not match immutable source")
        if annotation.get("citation_integrity") != "verified":
            errors.append(f"{eid}: source integrity must be verified")
        if annotation.get("citation_entailment") not in {"supported", "unsupported", "uncertain"}:
            errors.append(f"{eid}: semantic entailment annotation required")
        if annotation.get("stance") not in {"support", "contradict", "uncertain", "background"} or not annotation.get("reason"):
            errors.append(f"{eid}: stance and explanation required")
        if annotation.get("relevance") not in {"relevant", "background", "irrelevant", "unknown"}:
            errors.append(f"{eid}: relevance annotation required")
        fields = annotation.get("scope_fields", [])
        by_field = {f.get("field"): f for f in fields}
        if len(by_field) != len(fields):
            errors.append(f"{eid}: duplicate scope field annotations")
        for name in ("drug_ingredient", "event_term", "population", "dose", "route", "time_window"):
            field = by_field.get(name, {})
            if (field.get("outcome") not in {"matched", "mismatched", "unknown"} or
                    type(field.get("blocking")) is not bool or not field.get("reason")):
                errors.append(f"{eid}: scope field {name} requires label/blocking/reason")
        if annotation.get("eligible_as_direct_evidence") is True:
            for name in ("drug_ingredient", "event_term", "population", "dose", "route", "time_window"):
                field = by_field.get(name, {})
                if field.get("outcome") not in {"matched", "mismatched", "unknown"} or not field.get("reason"):
                    errors.append(f"{eid}: scope field {name} requires label/reason")
                if field.get("outcome") == "mismatched" or field.get("blocking") is True:
                    errors.append(f"{eid}: blocked scope cannot be direct evidence")
                if name in {"drug_ingredient", "event_term"} and field.get("outcome") != "matched":
                    errors.append(f"{eid}: direct evidence requires established targets")
                requested = claim.get("claim", {}).get({"drug_ingredient": "drug", "event_term": "event"}.get(name, name))
                if requested and field.get("outcome") != "matched":
                    errors.append(f"{eid}: requested scope {name} must be established for direct evidence")
        if doc.source == "faers" and (annotation.get("stance") in {"support", "contradict"} or annotation.get("eligible_as_direct_evidence") is True):
            errors.append(f"{eid}: FAERS is background, not direct causal evidence")
    required = row.get("required_gold_evidence_ids", [])
    optional = row.get("optional_gold_evidence_ids", [])
    if not set(required + optional).issubset(ids):
        errors.append("Gold evidence ID does not refer to an annotated span")
    for pair in row.get("contradiction_annotations", []):
        pair_ids = pair.get("evidence_ids", [])
        if (pair.get("kind") not in {"direct", "apparent", "methodological", "none", "uncertain"} or
                len(pair_ids) != 2 or len(set(pair_ids)) != 2 or not set(pair_ids).issubset(ids) or
                not pair.get("reason")):
            errors.append("Contradiction annotation requires two known distinct evidence IDs, kind and reason")
    if row.get("expected_assessment_status") in {"supported_for_scope", "contradicted_for_scope"}:
        if not required:
            errors.append("Conclusive label needs required evidence")
        for a in annotations:
            if a.get("evidence_id") in required and (a.get("citation_entailment") != "supported" or a.get("eligible_as_direct_evidence") is not True):
                errors.append("Required direct evidence must entail the statement and match its scope")
    return errors


def agreement_summary(pairs):
    """Unweighted Cohen kappa; N/A for no valid pairs or a degenerate marginal."""
    n = len(pairs)
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    agreed = sum(a == b for a, b in pairs)
    observed = agreed / n if n else None
    expected = sum(left[k] * right[k] for k in set(left) | set(right)) / (n * n) if n else None
    return {"pairs": n, "agreed": agreed, "agreement": observed,
            "cohen_kappa": (observed - expected) / (1 - expected) if expected is not None and expected < 1 else None,
            "confusion_counts": {f"{a}|{b}": count for (a, b), count in Counter(pairs).items()}}


def compare_reviews(claims, reviewer_a, reviewer_b, corpus):
    """Read both packets, report pending/invalid/disagreeing rows without merging."""
    def index(rows):
        values = {r["claim_id"]: r for r in rows}
        if len(values) != len(rows):
            raise ValueError("Duplicate claim IDs in reviewer packet")
        return values
    a, b = index(reviewer_a), index(reviewer_b)
    disagreements, ready, pending = [], [], []
    valid_pairs = []
    allowed = {c["claim_id"] for c in claims}
    if set(a) != allowed or set(b) != allowed:
        raise ValueError("Each reviewer packet must contain exactly the proposed claims")
    fields = ["expected_assessment_status", "expected_abstention", "required_gold_evidence_ids",
              "optional_gold_evidence_ids", "evidence_annotations", "contradiction_annotations", "critical_gaps"]
    def comparable(row):
        # Independent reviewers can use different local evidence IDs and wording
        # in their reasons. Compare source spans and labels rather than those IDs.
        spans = {e["evidence_id"]: (e.get("document_id"), e.get("source_version"), e.get("parsed_text_hash"),
                                  e.get("span_locator", {}).get("start"), e.get("span_locator", {}).get("end"))
                 for e in row.get("evidence_annotations", [])}
        value = {f: row.get(f) for f in fields}
        for f in ("required_gold_evidence_ids", "optional_gold_evidence_ids"):
            value[f] = sorted(spans[i] for i in row.get(f, []))
        value["evidence_annotations"] = sorted((spans[e["evidence_id"]], e.get("relevance"), e.get("stance"),
            e.get("eligible_as_direct_evidence"), e.get("citation_integrity"), e.get("citation_entailment"),
            tuple(sorted((f.get("field"), f.get("outcome"), f.get("blocking")) for f in e.get("scope_fields", []))))
            for e in row.get("evidence_annotations", []))
        return value
    for claim in claims:
        cid = claim["claim_id"]
        errors = {"reviewer_a": validate_annotation(a[cid], claim, corpus),
                  "reviewer_b": validate_annotation(b[cid], claim, corpus)}
        if a[cid].get("annotator_id") and a[cid].get("annotator_id") == b[cid].get("annotator_id"):
            errors["reviewer_b"].append("Two distinct independent reviewers required")
        if any(errors.values()):
            pending.append({"claim_id": cid, "issues": errors})
            continue
        valid_pairs.append((a[cid], b[cid]))
        values_a, values_b = comparable(a[cid]), comparable(b[cid])
        differences = [f for f in fields if values_a[f] != values_b[f]]
        if differences:
            disagreements.append({"claim_id": cid, "fields": differences, "adjudication": "required"})
        else:
            ready.append(cid)
    return {"claims": len(claims), "ready_for_team_adjudication": ready, "pending": pending,
            "disagreements": disagreements, "clinical_gold_published": False,
            "inter_reviewer_agreement": {
                name: agreement_summary([(left[name], right[name]) for left, right in valid_pairs])
                for name in ("expected_assessment_status", "expected_abstention")},
            "credential_verification": "Team responsibility; this check validates declared fields only."}
