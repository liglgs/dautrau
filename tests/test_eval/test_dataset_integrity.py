"""P26 rejects malformed provenance and split leakage before computing metrics."""

import json
from dataclasses import replace

import pytest

from eval.contracts import Prediction
from eval.corpus import Corpus, IntegrityError, read_jsonl
from eval.run_evaluation import EvaluationConfig, run_evaluation, validate_dataset
from scripts.seed_demo import MODEL, build


@pytest.fixture
def inputs(tmp_path):
    build(tmp_path)
    return EvaluationConfig(
        manifest=tmp_path / "corpus_manifest.json",
        claims=tmp_path / "claims.jsonl",
        annotations=tmp_path / "annotations.jsonl",
        recordings=tmp_path / "recordings.jsonl",
        model=MODEL,
        allow_synthetic=True,
        system="keyword",
        output=tmp_path / "results",
    )


def mutate_manifest(config, change):
    data = json.loads(config.manifest.read_text(encoding="utf-8"))
    change(data)
    config.manifest.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("value", ["false", 0, None])
def test_synthetic_flag_must_be_boolean(inputs, value):
    mutate_manifest(inputs, lambda data: data.update(synthetic=value, annotation_status="independently_reviewed"))
    with pytest.raises(IntegrityError, match="synthetic must be boolean"):
        run_evaluation(replace(inputs, allow_synthetic=False))
    assert not inputs.output.exists()


@pytest.mark.parametrize("version", [None, True, 2])
def test_only_supported_manifest_schema_is_accepted(inputs, version):
    mutate_manifest(inputs, lambda data: data.update(schema_version=version))
    with pytest.raises(IntegrityError, match="schema_version"):
        Corpus.load(inputs.manifest)


@pytest.mark.parametrize("version", [True, 0, "1"])
def test_document_version_is_positive_integer(inputs, version):
    mutate_manifest(inputs, lambda data: data["documents"][0].update(version=version))
    with pytest.raises(IntegrityError, match="document version"):
        Corpus.load(inputs.manifest)


@pytest.mark.parametrize("start", [False, 0.0])
def test_locator_offsets_are_integer_unicode_positions(inputs, start):
    mutate_manifest(inputs, lambda data: data["documents"][0]["units"][0].update(start=start))
    with pytest.raises(IntegrityError, match="locator"):
        Corpus.load(inputs.manifest)


@pytest.mark.parametrize("field", ["doc_id", "source_id"])
def test_source_identity_cannot_be_blank(inputs, field):
    mutate_manifest(inputs, lambda data: data["documents"][0].update({field: " "}))
    with pytest.raises(IntegrityError, match="identity"):
        Corpus.load(inputs.manifest)


@pytest.mark.parametrize(
    "override", [{"abstained": 1}, {"assessment_status": "proven_causality"}, {"relevant_evidence_ids": "broad-e1"}]
)
def test_invalid_gold_labels_do_not_generate_reports(inputs, override):
    labels = read_jsonl(inputs.annotations)
    labels[0].update(override)
    inputs.annotations.write_text("\n".join(json.dumps(row) for row in labels), encoding="utf-8")
    with pytest.raises(IntegrityError):
        run_evaluation(inputs)
    assert not inputs.output.exists()


def test_gold_document_leakage_is_detected_without_optional_related_doc_hints(inputs):
    corpus = Corpus.load(inputs.manifest)
    claims, labels = read_jsonl(inputs.claims), read_jsonl(inputs.annotations)
    for claim in claims:
        claim.pop("related_doc_ids")
    # A heldout annotation reuses a development document, though claim hints were omitted.
    labels[-1]["required_evidence_ids"] = []
    labels[-1]["relevant_evidence_ids"] = labels[0]["relevant_evidence_ids"]
    with pytest.raises(IntegrityError, match="document overlaps splits"):
        validate_dataset(claims, labels, corpus)


def test_related_documents_must_resolve_to_frozen_corpus(inputs):
    corpus = Corpus.load(inputs.manifest)
    claims = read_jsonl(inputs.claims)
    claims[0]["related_doc_ids"] = ["nonexistent-document"]
    with pytest.raises(IntegrityError, match="Related document"):
        validate_dataset(claims, read_jsonl(inputs.annotations), corpus)


def test_valid_frozen_fixture_still_runs_keyword(inputs):
    report = run_evaluation(inputs)
    assert report.errors == 0
    assert len(report.rows) == 4
    assert report.manifest["synthetic"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope_mismatches", "u:population"),
        ("scope_mismatches", [4]),
        ("scope_mismatches", ["u:unknown"]),
        ("scope_mismatches", ["v:population"]),
        ("scope_mismatches", ["u:population", "u:population"]),
        ("contradictions", "apparent:u|v"),
        ("contradictions", ["unknown:u|v"]),
        ("contradictions", ["apparent:v|u"]),
        ("contradictions", ["direct:u|u"]),
        ("contradictions", ["apparent:u|missing"]),
    ],
)
def test_prediction_detection_requires_valid_retrieved_keys(field, value):
    with pytest.raises(ValueError):
        Prediction.parse({"retrieved_ids": ["u"], field: value}, allowed_ids={"u", "v"})


def test_valid_prediction_detection_and_unmeasured_null():
    prediction = Prediction.parse(
        {"retrieved_ids": ["u", "v"], "scope_mismatches": ["u:population"], "contradictions": ["apparent:u|v"]},
        allowed_ids={"u", "v"},
    )
    assert prediction.contradictions == ["apparent:u|v"]
    assert Prediction.parse({"retrieved_ids": []}, allowed_ids=set()).scope_mismatches is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope_mismatches", "broad-doc-1-span-1:population"),
        ("scope_mismatches", None),
        ("scope_mismatches", ["missing:population"]),
        ("contradictions", ["apparent:missing|other"]),
    ],
)
def test_gold_detection_rejected_before_reporting(inputs, field, value):
    labels = read_jsonl(inputs.annotations)
    labels[0][field] = value
    inputs.annotations.write_text("\n".join(json.dumps(row) for row in labels), encoding="utf-8")
    with pytest.raises(IntegrityError):
        run_evaluation(inputs)
    assert not inputs.output.exists()


@pytest.mark.parametrize("field", ["scope_mismatches", "contradictions"])
def test_detection_only_gold_references_cannot_cross_splits(inputs, field):
    corpus = Corpus.load(inputs.manifest)
    claims, labels = read_jsonl(inputs.claims), read_jsonl(inputs.annotations)
    for claim in claims:
        claim.pop("related_doc_ids")
    labels[-1][field] = (
        ["broad-doc-1-span-1:population"]
        if field == "scope_mismatches"
        else ["apparent:apparent-doc-1-span-1|apparent-doc-2-span-1"]
    )
    with pytest.raises(IntegrityError, match="overlaps splits"):
        validate_dataset(claims, labels, corpus)


@pytest.mark.parametrize("hints", [True, False])
def test_source_versions_cannot_cross_splits(inputs, hints):
    corpus = Corpus.load(inputs.manifest)
    development = next(unit for unit in corpus.units if unit.doc_id.startswith("broad-"))
    # Keep distinct doc/unit IDs but give heldout evidence another version of the same source.
    corpus = replace(
        corpus,
        units=tuple(
            replace(unit, source=development.source, source_id=development.source_id, version=2)
            if unit.doc_id.startswith("heldout-support-")
            else unit
            for unit in corpus.units
        ),
    )
    claims, labels = read_jsonl(inputs.claims), read_jsonl(inputs.annotations)
    if not hints:
        for claim in claims:
            claim.pop("related_doc_ids")
    with pytest.raises(IntegrityError, match="overlaps splits"):
        validate_dataset(claims, labels, corpus)


def test_gold_detection_reference_must_be_visible_at_claim_cutoff(inputs):
    corpus = Corpus.load(inputs.manifest)
    claims, labels = read_jsonl(inputs.claims), read_jsonl(inputs.annotations)
    claims[0]["cutoff"] = "2026-09-29T00:00:00Z"
    labels[0]["required_evidence_ids"] = []
    labels[0]["relevant_evidence_ids"] = []
    with pytest.raises(IntegrityError, match="outside allowed context"):
        validate_dataset(claims, labels, corpus)
