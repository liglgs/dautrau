"""Authored counterexamples; no API, real credentials or clinical gold."""

import json
from dataclasses import replace

import pytest

from eval.baselines.keyword import BM25
from eval.baselines.scoped_rag import VERSION, RecordedScopedSynthesis, parse_response, prepare, source_quote
from eval.baselines.single_shot_rag import request_hash
from eval.corpus import Corpus, IntegrityError, Unit, digest
from eval.run_evaluation import EvaluationConfig, offline, run_evaluation
from scripts.record_scoped_rag import record, reparse
from src.services.llm import MockProvider


@pytest.fixture
def authored(tmp_path):
    text = "DrugX and EventY were reported in adults at 10 mg/day by oral route during 30 days. Randomized trial."
    dictionary = tmp_path / "dictionary.json"
    dictionary.write_text(json.dumps({"mode": "verified", "version": "authored-test", "drugs": [{
        "canonical": "DrugX", "aliases": ["CompoundX"], "source_ref": "authored", "license": "authored"}],
        "events": [{"canonical": "EventY", "aliases": [], "source_ref": "authored", "license": "authored"}]}))
    unit = Unit("u1", "doc1", "pubmed", "authored-source", 1, "DrugX EventY", text, digest(text.encode()),
                "2026-10-01T00:00:00Z", 0, len(text))
    corpus = Corpus((unit,), "authored-manifest", "2026-10-02T00:00:00Z", True, {})
    claim = {"claim_text": "Authored association only", "drug": "DrugX", "event": "EventY", "population": "adults",
             "dose": "10 mg/day", "route": "oral", "time_window": "30 days"}
    return tmp_path, dictionary, corpus, claim


def finding(corpus, claim, **updates):
    text = corpus.units[0].text
    result = {"alias": "E01", "quote": text, "direction": "supports", "uncertainty": "low", "study_type": "rct",
              "design_quote": "Randomized trial.", "scope": {field: {"value": claim[field], "quote": text}
              for field in ["drug", "event", "population", "dose", "route", "time_window"]}}
    result.update(updates)
    return result


def parsed(authored, raw, claim=None, corpus=None):
    _, dictionary, original_corpus, original_claim = authored
    corpus, claim = corpus or original_corpus, claim or original_claim
    payload = prepare(BM25(corpus), claim, "authored", dictionary_path=dictionary)
    return parse_response({"findings": [raw]}, payload, json.loads(dictionary.read_bytes()))


def test_genuine_full_scope_can_support_instead_of_always_abstaining(authored):
    _, _, corpus, claim = authored
    result = parsed(authored, finding(corpus, claim))
    assert result.assessment_status == "supported_for_scope" and result.abstained is False
    assert result.statements[0]["text"] == corpus.units[0].text


def test_requested_scope_cannot_be_copied_or_assumed(authored):
    _, _, corpus, claim = authored
    raw = finding(corpus, claim)
    raw["scope"]["dose"] = {"value": None, "quote": None}
    assert parsed(authored, raw).assessment_status == "insufficient_evidence"
    raw["scope"]["dose"] = {"value": "1000 mg/day", "quote": corpus.units[0].text}
    result = parsed(authored, raw)
    assert result.assessment_status == "insufficient_evidence" and result.statements == []
    assert result.trace[0]["excluded_findings"]
    # Literal unknown in a user field must not be matched to a known source scope.
    result = parsed(authored, finding(corpus, claim), claim={**claim, "dose": "unknown"})
    assert result.assessment_status == "insufficient_evidence"
    result = parsed(authored, finding(corpus, claim), claim={**claim, "dose": ">=10 mg/day"})
    assert result.assessment_status == "insufficient_evidence"
    raw = finding(corpus, claim)
    raw["scope"]["dose"] = {"value": ">=10 mg/day", "quote": corpus.units[0].text}
    assert parsed(authored, raw).statements == []


def test_bare_null_scope_is_unknown_and_other_invalid_shapes_still_fail(authored):
    _, dictionary, corpus, claim = authored
    raw = finding(corpus, claim)
    raw["scope"]["route"] = None
    result = parsed(authored, raw)
    assert result.assessment_status == "insufficient_evidence"
    assert result.trace[0]["checks"][0]["scope"]["route"] == "unknown"
    assert result.trace[0]["null_scope_fields"] == [{"alias": "E01", "field": "route"}]
    schema = prepare(BM25(corpus), claim, "authored", dictionary_path=dictionary)["response_schema"]
    assert {"type": "null"} in schema["$defs"]["Scope"]["properties"]["route"]["anyOf"]
    for invalid in ["oral", False, {"value": None, "quote": None, "extra": "injected"}]:
        raw["scope"]["route"] = invalid
        with pytest.raises(ValueError):
            parsed(authored, raw)
    del raw["scope"]["route"]
    with pytest.raises(ValueError):
        parsed(authored, raw)


def test_unknown_sentinel_without_quote_remains_unknown_not_requested_scope(authored):
    _, _, corpus, claim = authored
    raw = finding(corpus, claim)
    raw["scope"]["dose"] = {"value": "unknown", "quote": None}
    result = parsed(authored, raw)
    assert result.assessment_status == "insufficient_evidence"
    assert result.trace[0]["checks"][0]["scope"]["dose"] == "unknown"
    assert not result.trace[0]["excluded_findings"]
    assert result.trace[0]["scope_normalizations"]
    # A real number without a quote is still unverified, never treated as null.
    raw["scope"]["dose"] = {"value": "1000 mg/day", "quote": None}
    assert parsed(authored, raw).statements == []


def test_only_pinned_equivalent_alias_literal_in_source_quote_is_allowed(authored):
    _, _, corpus, claim = authored
    raw = finding(corpus, claim)
    raw["scope"]["drug"] = {"value": "CompoundX", "quote": "DrugX"}
    result = parsed(authored, raw)
    assert result.assessment_status == "supported_for_scope"
    assert result.trace[0]["scope_normalizations"][0]["source_aliases"] == ["DrugX"]
    for value, quote in [("OtherDrug", "DrugX"), ("CompoundX", "EventY"), ("CompoundX", "XDrugX")]:
        raw["scope"]["drug"] = {"value": value, "quote": quote}
        assert parsed(authored, raw).statements == []


def test_narrow_scope_does_not_support_broader_claim(authored):
    _, _, corpus, claim = authored
    result = parsed(authored, finding(corpus, claim), claim={**claim, "population": None})
    assert result.assessment_status == "insufficient_evidence"
    assert result.trace[0]["checks"][0]["scope"]["population"] == "unknown"


def test_faers_never_becomes_direct_support_even_if_model_says_so(authored):
    _, _, corpus, claim = authored
    faers = replace(corpus, units=(replace(corpus.units[0], source="faers"),))
    assert parsed(authored, finding(corpus, claim), corpus=faers).assessment_status == "insufficient_evidence"


def test_route_mismatch_is_reported_and_does_not_answer_claim(authored):
    _, _, corpus, claim = authored
    result = parsed(authored, finding(corpus, claim), claim={**claim, "route": "intravenous"})
    assert result.assessment_status == "scope_mismatch" and result.abstained
    assert result.scope_mismatches == ["u1:route"]


def test_observational_null_cannot_be_direct_rebuttal(authored):
    _, _, corpus, claim = authored
    result = parsed(authored, finding(corpus, claim, direction="contradicts", study_type="observational"))
    assert result.assessment_status == "insufficient_evidence"
    opposing_text = "DrugX reduced EventY compared with placebo in adults at 10 mg/day by oral route during 30 days. Randomized trial."
    opposing = replace(corpus, units=(replace(corpus.units[0], text=opposing_text, end=len(opposing_text),
                                            document_hash=digest(opposing_text.encode())),))
    result = parsed(authored, finding(opposing, claim, direction="contradicts"), corpus=opposing)
    assert result.assessment_status == "contradicted_for_scope" and not result.abstained


def test_cohort_normalization_does_not_make_rct_or_mutate_raw_response(authored):
    _, dictionary, corpus, claim = authored
    raw = {"findings": [finding(corpus, claim, direction="contradicts", study_type="cohort")]}
    before = json.dumps(raw)
    payload = prepare(BM25(corpus), claim, "authored", dictionary_path=dictionary)
    result = parse_response(raw, payload, json.loads(dictionary.read_bytes()))
    assert result.assessment_status == "insufficient_evidence"
    assert json.dumps(raw) == before
    assert result.trace[0]["study_type_normalizations"] == [
        {"alias": "E01", "submitted": "cohort", "normalized": "observational"}]
    raw["findings"][0]["study_type"] = "made_up_design"
    with pytest.raises(ValueError):
        parse_response(raw, payload, json.loads(dictionary.read_bytes()))


def test_fabricated_quote_excluded_and_foreign_alias_is_error(authored):
    _, _, corpus, claim = authored
    result = parsed(authored, finding(corpus, claim, quote="Fabricated quotation."))
    assert result.statements == [] and result.abstained
    with pytest.raises(ValueError, match="outside retrieved"):
        parsed(authored, finding(corpus, claim, alias="E99"))


def test_meta_analysis_maps_to_review_without_bypassing_quote_or_rct_checks(authored):
    _, dictionary, corpus, claim = authored
    text = corpus.units[0].text.replace("Randomized trial.", "Meta-analysis of randomized trials.")
    corpus = replace(corpus, units=(replace(corpus.units[0], text=text, end=len(text),
                                          document_hash=digest(text.encode())),))
    raw = {"findings": [finding(corpus, claim, direction="contradicts", study_type="meta-analysis",
                               design_quote="Meta-analysis of randomized trials.")]}
    before = json.dumps(raw)
    payload = prepare(BM25(corpus), claim, "authored", dictionary_path=dictionary)
    result = parse_response(raw, payload, json.loads(dictionary.read_bytes()))
    assert result.assessment_status == "insufficient_evidence"  # not direct RCT rebuttal
    assert len(result.statements) == 1 and not result.trace[0]["excluded_findings"]
    assert result.trace[0]["study_type_normalizations"] == [
        {"alias": "E01", "submitted": "meta-analysis", "normalized": "review"}]
    assert json.dumps(raw) == before
    for invalid_design in [None, "Invented design quote."]:
        raw["findings"][0]["design_quote"] = invalid_design
        result = parse_response(raw, payload, json.loads(dictionary.read_bytes()))
        assert not result.statements and result.trace[0]["excluded_findings"]


def test_whitespace_only_restores_original_source_span_without_fuzzy_edits(authored):
    _, _, corpus, claim = authored
    text = corpus.units[0].text.replace("in adults", "in  adults")
    corpus = replace(corpus, units=(replace(corpus.units[0], text=text),))
    raw = finding(corpus, claim)
    raw["quote"] = text.replace("in  adults", "in adults")
    raw["scope"]["population"]["quote"] = "in adults"
    result = parsed(authored, raw, corpus=corpus)
    assert result.assessment_status == "supported_for_scope"
    assert result.statements[0]["text"] == text
    assert result.trace[0]["whitespace_restorations"]
    assert source_quote("in adults", ["in\n adults"]) == "in\n adults"
    assert source_quote("in adults", ["in  adults / in\n adults"]) is None
    for quote in ["drugX", "11 mg/day", "DrugX.", "DrugX EventY"]:
        assert source_quote(quote, [text]) is None
    raw["quote"] = raw["quote"].replace("30 days", "90 days")
    assert parsed(authored, raw, corpus=corpus).statements == []


def test_normalization_ignores_ingredient_in_free_text_and_annotation_fields(authored):
    _, dictionary, corpus, claim = authored
    unknown = {**claim, "drug": "UnresolvedBrand", "claim_text": "DrugX EventY", "claim_id": "leak",
               "family_id": "leak", "assessment_status": "supported_for_scope"}
    payload = prepare(BM25(corpus), unknown, "authored", dictionary_path=dictionary)
    assert payload["normalization"]["requires_review"] and payload["evidence"] == []
    assert set(payload["claim"]) <= {"claim_text", "drug", "event", "population", "dose", "route", "time_window", "cutoff"}
    result = parse_response({"findings": []}, payload, json.loads(dictionary.read_bytes()))
    assert result.assessment_status == "requires_human_review"
    normal = prepare(BM25(corpus), claim, "authored", dictionary_path=dictionary)
    extra = prepare(BM25(corpus), {**claim, "claim_id": "different", "family_id": "answer"}, "authored", dictionary_path=dictionary)
    assert request_hash(normal) == request_hash(extra)


def test_retrieval_spelling_balance_document_cap_and_cutoff(authored):
    _, dictionary, corpus, claim = authored
    data = json.loads(dictionary.read_bytes())
    data["events"][0]["canonical"] = "diarrhoea"
    dictionary.write_text(json.dumps(data))
    unit = corpus.units[0]
    text = "DrugX diarrhea " * 8
    units = [replace(unit, unit_id=f"f{i}", doc_id=f"faers{i}", source="faers", text=text, title="DrugX diarrhea")
             for i in range(30)]
    units += [replace(unit, unit_id=f"p{i}", doc_id="primary", source="pubmed", text=text, title="DrugX diarrhea")
              for i in range(8)]
    units += [replace(unit, unit_id="future", doc_id="future", text=text, title="DrugX diarrhea",
                      available_at="2026-10-03T00:00:00Z")]
    corpus = replace(corpus, units=tuple(units))
    payload = prepare(BM25(corpus), {**claim, "event": "diarrhoea"}, "authored", dictionary_path=dictionary)
    evidence = payload["evidence"]
    assert any(u["source"] == "pubmed" for u in evidence)
    assert sum(u["source"] == "faers" for u in evidence) <= 4
    assert sum(u["doc_id"] == "primary" for u in evidence) <= 3
    assert "future" not in payload["alias_to_unit_id"].values()
    assert "DrugX diarrhea" in payload["retrieval_queries"]


def make_dataset(authored):
    root, dictionary, corpus, claim = authored
    unit = corpus.units[0]
    (root / "source.txt").write_text(unit.text, encoding="utf-8")
    claims_path = root / "claims.jsonl"
    claims_path.write_text(json.dumps({"claim_id": "authored", "family_id": "authored", "split": "development", **claim}) + "\n")
    manifest = root / "corpus_manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "mode": "replay", "synthetic": True,
        "cutoff": corpus.cutoff, "versions": {}, "documents": [{"doc_id": unit.doc_id, "source": unit.source,
        "source_id": unit.source_id, "version": 1, "title": unit.title, "path": "source.txt", "sha256": unit.document_hash,
        "available_at": unit.available_at, "units": [{"unit_id": unit.unit_id, "text": unit.text, "start": 0, "end": len(unit.text)}]}]}))
    return root, dictionary, corpus, claim, manifest


def test_empty_pool_document_fallback_respects_cutoff_and_keeps_event_unverified(authored):
    _, dictionary, corpus, claim = authored
    event = "gastrointestinal haemorrhage"
    data = json.loads(dictionary.read_bytes())
    data["events"][0]["canonical"] = event
    dictionary.write_text(json.dumps(data))
    unit = corpus.units[0]
    units = [replace(unit, unit_id="drug-part", title="Report", source="faers", text="DrugX was reported."),
             replace(unit, unit_id="event-part", title="Report", source="faers", text="Gastrointestinal haemorrhage was reported."),
             replace(unit, unit_id="broader-primary", doc_id="doc2", title="Trial", text="DrugX and gastrointestinal bleeding were reported."),
             replace(unit, unit_id="unrelated-event", doc_id="doc3", title="Other report", text="Gastrointestinal haemorrhage was reported."),
             replace(unit, unit_id="future", doc_id="future", title="Future", text="DrugX gastrointestinal haemorrhage",
                     available_at="2027-01-01T00:00:00Z")]
    corpus = replace(corpus, units=tuple(units))
    claim = {**claim, "event": event, "cutoff": "2026-10-02T00:00:00Z"}
    payload = prepare(BM25(corpus), claim, "authored", dictionary_path=dictionary)
    ids = set(payload["alias_to_unit_id"].values())
    assert "empty_pool_fallback" in payload["protocol"]
    assert {"drug-part", "event-part", "broader-primary"} <= ids
    assert not ids.intersection({"future", "unrelated-event"})
    # Broader lexical retrieval must not establish event equivalence.
    alias = next(a for a, uid in payload["alias_to_unit_id"].items() if uid == "broader-primary")
    raw = finding(corpus, claim, alias=alias, quote=units[2].text, study_type="unknown", design_quote=None)
    raw["scope"] = {f: {"value": None, "quote": None} for f in raw["scope"]}
    raw["scope"]["drug"] = {"value": "DrugX", "quote": "DrugX"}
    raw["scope"]["event"] = {"value": event, "quote": "gastrointestinal bleeding"}
    prediction = parse_response({"findings": [raw]}, payload, data)
    assert prediction.assessment_status == "insufficient_evidence" and prediction.statements == []
    # Old empty checkpoints cannot be reused against newly supplied source text.
    original = {**payload, "evidence": [], "alias_to_unit_id": {}, "rendered_untrusted": ""}
    path = dictionary.parent / "old-empty.jsonl"
    path.write_text(json.dumps({"kind": VERSION, "model": "authored", "request": original,
                               "request_sha256": request_hash(original), "raw_response": {"findings": []}}), encoding="utf-8")
    with offline(), pytest.raises(IntegrityError, match="live fallback disabled"):
        RecordedScopedSynthesis(path, model="authored", dictionary_path=dictionary).synthesize(payload)


def test_record_preview_cache_and_evaluator_no_live_fallback(authored):
    root, dictionary, corpus, claim, manifest = make_dataset(authored)
    response = {"findings": [finding(corpus, claim)]}
    mock = MockProvider({VERSION: response}, model="authored")
    with offline():
        preview = record(root, "authored", "development", dictionary_path=dictionary)
        assert preview["mode"] == "preview" and not (root / f"{VERSION}-development.responses.jsonl").exists()
        first = record(root, "authored", "development", mock, dictionary_path=dictionary)
        assert first["claims"][0]["assessment_status"] == "supported_for_scope"
        path = root / f"{VERSION}-development.responses.jsonl"
        before = path.read_bytes()
        preview_again = record(root, "preview-no-model-calls", "development", dictionary_path=dictionary)
        assert preview_again["mode"] == "preview" and path.read_bytes() == before
        second = record(root, "authored", "development", mock, dictionary_path=dictionary)
        assert len(mock.calls) == 1 and second["claims"][0]["recording"] == "cached"
        assert path.read_bytes() == before
    annotation = root / "annotations.jsonl"
    annotation.write_text(json.dumps({"claim_id": "authored", "relevant_evidence_ids": ["u1"], "required_evidence_ids": ["u1"],
        "assessment_status": "supported_for_scope", "abstained": False, "scope_mismatches": [], "contradictions": [],
        "statement_reviews": []}) + "\n")
    config = EvaluationConfig(manifest=manifest, claims=root / "claims.jsonl", annotations=annotation, recordings=path,
        model="authored", system="scoped_rag", scoped_dictionary=dictionary, allow_synthetic=True, output=root / "evaluation")
    result = run_evaluation(config)
    assert result.errors == 0 and result.rows[0]["metrics"]["assessment_correct"]
    assert result.manifest["experiment_interpretation"].startswith("post-hoc")
    payload = prepare(BM25(corpus), {**claim, "time_window": "90 days"}, "authored", dictionary_path=dictionary)
    with offline(), pytest.raises(IntegrityError, match="live fallback disabled"):
        RecordedScopedSynthesis(path, model="authored", dictionary_path=dictionary).synthesize(payload)


def test_invalid_raw_response_kept_and_only_valid_attempt_is_cached(authored):
    root, dictionary, corpus, claim, _ = make_dataset(authored)
    bad = MockProvider({VERSION: "{broken json"}, model="authored")
    report = record(root, "authored", "development", bad, dictionary_path=dictionary)
    assert report["claims"][0]["error"]
    path = root / f"{VERSION}-development.responses.jsonl"
    assert json.loads(path.read_text().splitlines()[0])["raw_response"] == "{broken json"
    good = MockProvider({VERSION: {"findings": [finding(corpus, claim)]}}, model="authored")
    assert not record(root, "authored", "development", good, dictionary_path=dictionary)["claims"][0]["error"]
    assert len(good.calls) == 1 and len(path.read_text().splitlines()) == 2
    record(root, "authored", "development", good, dictionary_path=dictionary)
    assert len(good.calls) == 1


def test_excluded_findings_are_visible_and_v1_recordings_are_preserved(authored, capsys):
    root, dictionary, corpus, claim, _ = make_dataset(authored)
    historical = root / "scoped-rag-v1-development.responses.jsonl"
    historical.write_text("historical failed response\n")
    before = historical.read_bytes()
    raw = finding(corpus, claim)
    raw["scope"]["route"] = {"value": "intravenous", "quote": "oral route"}
    mock = MockProvider({VERSION: {"findings": [raw]}}, model="authored")
    report = record(root, "authored", "development", mock, dictionary_path=dictionary)
    row = report["claims"][0]
    assert row["error"] is None and row["accepted_findings"] == 0
    assert row["excluded_findings"] == 1 and row["needs_quote_review"]
    assert row["excluded_finding_details"] == [{"alias": "E01", "reason": "Unverified scope anchor: route",
                                              "reasons": ["Unverified scope anchor: route"]}]
    assert "needs_quote_review" in capsys.readouterr().out
    assert historical.read_bytes() == before
    repeated = record(root, "authored", "development", mock, dictionary_path=dictionary)
    assert repeated["claims"][0]["needs_quote_review"] and len(mock.calls) == 1


def test_offline_reparse_preserves_originals_and_rejects_context_changes(authored):
    root, dictionary, corpus, claim, _ = make_dataset(authored)
    mock = MockProvider({VERSION: {"findings": [finding(corpus, claim)]}}, model="authored")
    record(root, "authored", "development", mock, dictionary_path=dictionary)
    original_path = root / f"{VERSION}-development.responses.jsonl"
    original = json.loads(original_path.read_text(encoding="utf-8"))
    # Historical inference stays historical, with its original prompt and hash.
    original["kind"] = "scoped-rag-v2"
    original["request"]["protocol"]["version"] = "scoped-rag-v2"
    original["request"]["prompt"] = "Historical v2 prompt"
    original["request_sha256"] = request_hash(original["request"])
    historical = root / "scoped-rag-v2-development.responses.jsonl"
    historical.write_text(json.dumps(original) + "\n")
    before = historical.read_bytes()
    expected = prepare(BM25(Corpus.load(root / "corpus_manifest.json")), claim, "authored", dictionary_path=dictionary)
    assert original["request"]["rendered_untrusted"] == expected["rendered_untrusted"]
    with offline():
        report = reparse(root, historical, "development", dictionary_path=dictionary)
    assert report["claims"][0]["error"] is None, report["claims"][0]
    assert report["live_calls"] == 0 and report["new_model_run"] is False and not report["prompt_resent"]
    assert report["claims"][0]["assessment_status"] == "supported_for_scope"
    assert report["claims"][0]["original_inference_version"] == "scoped-rag-v2"
    assert historical.read_bytes() == before and len(mock.calls) == 1
    # Earlier retrieval checkpoints with other context do not hide a later
    # verified recording. Their hashes remain checked and skips are disclosed.
    outdated = json.loads(json.dumps(original))
    outdated["request"]["evidence"] = []
    outdated["request_sha256"] = request_hash(outdated["request"])
    historical.write_text(json.dumps(outdated) + "\n" + json.dumps(original) + "\n")
    with offline():
        report = reparse(root, historical, "development", dictionary_path=dictionary)
    assert report["claims"][0]["error"] is None
    assert report["claims"][0]["skipped_incompatible_contexts"] == [
        {"request_sha256": outdated["request_sha256"], "changed_fields": ["evidence"]}]
    # Even a recomputed hash cannot make altered source text match the frozen corpus.
    original["request"]["evidence"][0]["text"] += " fabricated"
    original["request_sha256"] = request_hash(original["request"])
    historical.write_text(json.dumps(original) + "\n")
    with offline():
        report = reparse(root, historical, "development", dictionary_path=dictionary)
    assert report["claims"][0]["error"]["type"] == "IntegrityError"
    assert "frozen corpus" in report["claims"][0]["error"]["message"]
    original["request_sha256"] = "tampered"
    historical.write_text(json.dumps(original) + "\n")
    with offline():
        report = reparse(root, historical, "development", dictionary_path=dictionary)
    assert "hash mismatch" in report["claims"][0]["error"]["message"]


def test_dictionary_pinned_and_record_hash_tampering_rejected(authored):
    root, dictionary, corpus, claim = authored
    pinned = replace(corpus, versions={"dictionary_sha256": "wrong"})
    with pytest.raises(IntegrityError, match="dictionary changed"):
        prepare(BM25(pinned), claim, "authored", dictionary_path=dictionary)
    path = root / "record.jsonl"
    payload = prepare(BM25(corpus), claim, "authored", dictionary_path=dictionary)
    path.write_text(json.dumps({"kind": VERSION, "model": "authored", "request": payload,
                               "request_sha256": "tampered", "raw_response": {"findings": []}}) + "\n")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        RecordedScopedSynthesis(path, model="authored", dictionary_path=dictionary)


def test_parser_only_reprocessing_reuses_exact_model_input_with_both_hashes(authored):
    root, dictionary, corpus, claim, _ = make_dataset(authored)
    mock = MockProvider({VERSION: {"findings": [finding(corpus, claim)]}}, model="authored")
    record(root, "authored", "development", mock, dictionary_path=dictionary)
    path = root / f"{VERSION}-development.responses.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["request"]["protocol"].pop("postprocessor_version")
    row["request"]["protocol"]["implementation_sha256"]["eval/baselines/scoped_rag.py"] = "historical-parser-code"
    row["request_sha256"] = request_hash(row["request"])
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    before = path.read_bytes()
    report = record(root, "authored", "development", mock, dictionary_path=dictionary)
    assert report["claims"][0]["recording"] == "cached_reprocessed" and len(mock.calls) == 1
    assert report["claims"][0]["original_request_sha256"] == row["request_sha256"]
    assert path.read_bytes() == before
    synthesis = RecordedScopedSynthesis(path, model="authored", dictionary_path=dictionary)
    payload = prepare(BM25(Corpus.load(root / "corpus_manifest.json")), claim, "authored", dictionary_path=dictionary)
    prediction = synthesis.synthesize(payload)
    assert prediction.usage["live_calls"] == 0
    assert prediction.usage["request_sha256"] != prediction.usage["processing_request_sha256"]
    changed = {**payload, "prompt": "Changed instructions"}
    with offline(), pytest.raises(IntegrityError, match="live fallback disabled"):
        synthesis.synthesize(changed)
    changed_dependency = json.loads(json.dumps(payload))
    changed_dependency["protocol"]["implementation_sha256"]["src/services/evidence/normalize.py"] = "changed-normalizer"
    with offline(), pytest.raises(IntegrityError, match="live fallback disabled"):
        synthesis.synthesize(changed_dependency)


def test_unresolved_brand_checkpoint_records_without_any_model_call(authored):
    root, dictionary, _, claim, _ = make_dataset(authored)
    (root / "claims.jsonl").write_text(json.dumps({"claim_id": "brand", "split": "development", **claim,
        "drug": "UnresolvedBrand", "claim_text": "DrugX EventY"}) + "\n")
    mock = MockProvider({}, model="authored")
    report = record(root, "authored", "development", mock, dictionary_path=dictionary)
    assert report["claims"][0]["assessment_status"] == "requires_human_review"
    assert report["claims"][0]["recording"] == "local_checkpoint" and mock.calls == []
    repeated = record(root, "authored", "development", mock, dictionary_path=dictionary)
    assert repeated["claims"][0]["recording"] == "cached" and mock.calls == []
