"""Authored offline checks for the P3/P4 handoff, never clinical gold."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import eval.person3_dataset as dataset_module
import scripts.record_person3_evaluation as recording_module
from eval.baselines.keyword import BM25
from eval.baselines.single_shot_rag import parse_wire_prediction, request_payload
from eval.contracts import PREDICTION_SCHEMA, Prediction
from eval.corpus import Corpus, IntegrityError, digest, read_jsonl
from eval.person3_agent import RecordedProvider, RecordingProvider, predict, run_agent
from eval.person3_dataset import convert_annotation, covering_units, export_dataset
from eval.person3_provisional import SPEC, build_ai_reference
from eval.run_evaluation import EvaluationConfig, offline, run_evaluation
from scripts.record_person3_evaluation import record_rag_claim, record_rag_only
from src.models.schemas import SourceDocument
from src.services.evidence.annotation_review import agreement_summary
from src.services.llm import MockProvider

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "data/mvp-candidates-50-2026-10-02.zip"
BENCHMARK = ROOT / "data/benchmark"


def test_ai_reference_is_explicit_and_preserves_expert_inputs(tmp_path):
    if not BUNDLE.is_file():
        pytest.skip("Private candidate bundle is not present in CI")
    before = {name: digest((BENCHMARK / name).read_bytes()) for name in
              ("reviewer_a.jsonl", "reviewer_b.jsonl", "mvp_gold.jsonl")}
    target = tmp_path / "ai-packet"
    result = build_ai_reference(BUNDLE, BENCHMARK, target)
    assert result["claims"] == 20 and result["exact_quotes"] == 9
    assert result["status_counts"] == {"insufficient_evidence": 16, "requires_human_review": 4}
    assert result["original_expert_files_sha256"] == before
    assert all(digest((BENCHMARK / n).read_bytes()) == h for n, h in before.items())
    config = EvaluationConfig(manifest=target / "corpus_manifest.json", claims=target / "claims.jsonl",
                              annotations=target / "annotations.jsonl", system="keyword", output=tmp_path / "report")
    with pytest.raises(IntegrityError, match="allow-provisional"):
        run_evaluation(config)
    from dataclasses import replace
    result = run_evaluation(replace(config, allow_provisional=True))
    assert result.errors == 0
    assert result.manifest["annotation_provenance"]["heldout_exposed_to_annotator"]
    assert result.summaries["keyword"]["clinical_validation_claimed"] is False
    assert "Clinical accuracy is not measured" in result.markdown
    review = json.loads((target / "ai-reference-review.json").read_text(encoding="utf-8"))
    assert all(c["clinical_approval"] is False for c in review["claims"])
    assert all(not c["evidence_annotations"] for c in review["claims"] if c["claim_id"].endswith("05"))
    for c in review["claims"]:
        for a in c["evidence_annotations"]:
            doc = next(d for d in json.loads(config.manifest.read_bytes())["documents"] if d["doc_id"] == a["doc_id"])
            text = (target / doc["path"]).read_bytes().decode("utf-8")
            assert digest(text.encode()) == a["source_sha256"]
            assert text[a["span_locator"]["start"]:a["span_locator"]["end"]] == a["quote"]
    config.annotations.write_bytes(config.annotations.read_bytes() + b"\n")
    with pytest.raises(IntegrityError, match="annotation hash"):
        run_evaluation(replace(config, allow_provisional=True))


def test_ai_review_cannot_be_relabelled_as_an_expert(tmp_path):
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["annotator_role"] = "clinical_pharmacist"
    path = tmp_path / "forged-role.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(IntegrityError, match="disclose AI authorship"):
        build_ai_reference(BUNDLE, BENCHMARK, tmp_path / "rejected", specification=path)
    assert not (tmp_path / "rejected").exists()


def test_ai_review_rejects_a_quote_not_in_pinned_snapshot(tmp_path):
    if not BUNDLE.is_file():
        pytest.skip("Private candidate bundle is not present in CI")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["families"]["metformin"]["anchors"][0]["quote"] = "Fabricated 90-day dose-specific result."
    path = tmp_path / "bad-quote.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(IntegrityError, match="uniquely match"):
        build_ai_reference(BUNDLE, BENCHMARK, tmp_path / "rejected", specification=path)
    assert not (tmp_path / "rejected").exists()


def test_rag_schema_specifies_statement_keys_and_classification():
    statement = PREDICTION_SCHEMA["$defs"]["Statement"]
    assert set(statement["required"]) == {"text", "kind", "evidence_ids"}
    assert statement["properties"]["kind"]["enum"] == ["fact", "inference", "hypothesis"]
    with pytest.raises(ValueError, match="classification"):
        Prediction.parse({"retrieved_ids": [], "statements": [{"text": "x", "classification": "fact"}]}, allowed_ids=set())


def test_invalid_rag_response_is_retained_without_fabricating_a_record(authored_corpus):
    root, _, corpus, claim, _ = authored_corpus
    target = root / "recordings.jsonl"
    mock = MockProvider({"single_shot_rag": {"retrieved_ids": ["E01"],
                        "assessment_status": "insufficient_evidence", "abstained": True,
                        "scope_mismatches": [], "contradictions": [],
                        "statements": [{"text": "Authored example", "classification": "fact"}]}})
    with pytest.raises(ValueError, match="classification"):
        record_rag_claim(BM25(corpus), claim, "authored", mock, target)
    assert not target.exists()
    rows = read_jsonl(target.with_suffix(".rag-responses.jsonl"))
    assert len(rows) == 1 and "classification" in rows[0]["text"]


def test_rag_only_preserves_agent_and_reuses_valid_synthesis(authored_corpus):
    root, manifest, _, claim, _ = authored_corpus
    data = json.loads(manifest.read_bytes())
    data.update(synthetic=False, annotation_status="independently_reviewed")
    manifest.write_text(json.dumps(data), encoding="utf-8")
    raw = {"claim_id": "authored-claim", "split": "development", **claim}
    dataset_module.write_rows(root / "claims.jsonl", [raw])
    previous_path = root / "recording-report-development.json"
    dataset_module.write_json(previous_path, {"model": "authored", "corpus_manifest_sha256": digest(manifest.read_bytes()),
        "claims": [{"claim_id": raw["claim_id"], "agent_error": None, "replay_verified": True,
                    "rag_error": {"message": "Authored original formatting failure"}}]})
    # Empty provider log is sufficient for this authored test; no actual graph/model call is claimed.
    agent_path = root / "recordings-development.agent.jsonl"
    agent_path.write_text("", encoding="utf-8")
    before = {p: p.read_bytes() for p in (previous_path, agent_path)}
    mock = MockProvider({"single_shot_rag": {"retrieved_ids": ["E01"],
        "assessment_status": "insufficient_evidence", "abstained": True,
        "scope_mismatches": [], "contradictions": [],
        "statements": [{"text": "Authored scope is incomplete.", "kind": "inference", "evidence_ids": ["E01"]}]}})
    assert record_rag_only(root, "authored", "development", mock) == 0
    assert len(mock.calls) == 1
    assert record_rag_only(root, "authored", "development", mock) == 0
    assert len(mock.calls) == 1
    assert all(p.read_bytes() == value for p, value in before.items())
    report = json.loads((root / "rag-recording-report-development.json").read_bytes())
    assert report["agent_live_calls"] == 0 and report["claims"][0]["rag_recording"] == "cached"
    assert len(read_jsonl(root / "rag-attempts-development.jsonl")) == 2
    incomplete = json.loads(previous_path.read_bytes())
    incomplete["claims"][0]["replay_verified"] = False
    dataset_module.write_json(previous_path, incomplete)
    with pytest.raises(IntegrityError, match="Wait for all agent"):
        record_rag_only(root, "authored", "development", mock)
    assert len(mock.calls) == 1


def test_rag_aliases_map_exactly_without_relabelling_statements():
    evidence = [{"unit_id": "P3U-z", "text": "Authored first", "source": "pubmed"},
                {"unit_id": "P3U-a", "text": "Authored second", "source": "dailymed"}]
    payload = request_payload({"drug": "authored", "event": "authored"}, evidence, "authored")
    assert payload["alias_to_unit_id"] == {"E01": "P3U-z", "E02": "P3U-a"}
    assert payload["response_schema"]["$defs"]["Statement"]["properties"]["evidence_ids"]["items"]["enum"] == ["E01", "E02"]
    raw = {"retrieved_ids": ["E01", "E02"], "assessment_status": "requires_human_review", "abstained": True,
           "scope_mismatches": ["E01:route"], "contradictions": ["apparent:E01|E02"],
           "statements": [{"text": "Authored inference.", "kind": "inference", "evidence_ids": ["E02"]}]}
    result = parse_wire_prediction(raw, payload)
    assert result.retrieved_ids == ["P3U-z", "P3U-a"]
    assert result.scope_mismatches == ["P3U-z:route"]
    assert result.contradictions == ["apparent:P3U-a|P3U-z"]
    assert result.statements == [{"text": "Authored inference.", "kind": "inference", "evidence_ids": ["P3U-a"]}]
    assert raw["statements"][0]["evidence_ids"] == ["E02"]
    raw["statements"][0]["evidence_ids"] = ["P3U-13"]
    with pytest.raises(ValueError, match="outside retrieved"):
        parse_wire_prediction(raw, payload)


def test_rag_payload_hash_pins_actual_rendered_context():
    from eval.baselines.single_shot_rag import request_hash
    payload = request_payload({"drug": "authored", "event": "authored"},
                              [{"unit_id": "a", "text": "Authored text", "source": "pubmed"}], "authored")
    before = request_hash(payload)
    payload["rendered_untrusted"] += "changed"
    assert request_hash(payload) != before


def test_export_real_candidates_without_gold(tmp_path):
    if not BUNDLE.is_file():
        pytest.skip("Private candidate bundle is not present in CI")
    target = tmp_path / "packet"
    result = export_dataset(BUNDLE, BENCHMARK, target)
    assert result["documents"] == 50
    assert result["claims"] == 20
    assert result["split_counts"] == {"development": 5, "heldout": 15}
    assert not result["clinical_metrics_ready"]
    assert not (target / "annotations.jsonl").exists()
    corpus = Corpus.load(target / "corpus_manifest.json")
    manifest = json.loads((target / "corpus_manifest.json").read_text(encoding="utf-8"))
    assert manifest["cutoff_kind"] == "last_snapshot_available_at"
    assert manifest["cutoff"] > manifest["proposed_collection_start"]
    assert len(corpus.units) == result["retrieval_units"]
    assert all(u.text for u in corpus.units)
    assert all(c["assessment_status"] is None for c in read_jsonl(target / "annotations.template.jsonl"))
    with pytest.raises(FileExistsError):
        export_dataset(BUNDLE, BENCHMARK, target)
    with pytest.raises(IntegrityError, match="independently reviewed"):
        run_evaluation(EvaluationConfig(manifest=target / "corpus_manifest.json",
                       claims=target / "claims.jsonl", annotations=target / "annotations.template.jsonl"))
    first = manifest["documents"][0]
    path = target / first["path"]
    path.write_bytes(path.read_bytes() + b" changed")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        Corpus.load(target / "corpus_manifest.json")


def test_pending_reviews_cannot_publish(tmp_path):
    if not BUNDLE.is_file():
        pytest.skip("Private candidate bundle is not present in CI")
    approval = tmp_path / "fake-approval.json"
    approval.write_text("{}", encoding="utf-8")
    with pytest.raises(IntegrityError, match="independent specialist"):
        export_dataset(BUNDLE, BENCHMARK, tmp_path / "rejected", approval=approval)
    assert not (tmp_path / "rejected/annotations.jsonl").exists()


@pytest.fixture
def authored_corpus(tmp_path):
    text = "Authored integration test: metformin and diarrhoea were recorded."
    snapshot = tmp_path / "source.txt"
    snapshot.write_bytes(text.encode())
    manifest = tmp_path / "corpus_manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "mode": "replay", "synthetic": True,
        "cutoff": "2026-10-02T12:00:00+00:00", "versions": {}, "documents": [{
        "doc_id": "test-doc", "source": "pubmed", "source_id": "authored-123", "version": 2,
        "path": "source.txt", "sha256": digest(text.encode()), "title": "Authored test only",
        "available_at": "2026-10-02T11:00:00+00:00", "units": [
            {"unit_id": "test-unit", "start": 0, "end": len(text), "text": text}]}]}), encoding="utf-8")
    corpus = Corpus.load(manifest)
    claim = {"claim_text": "Authored metformin / diarrhoea test", "drug": "metformin", "event": "diarrhoea"}
    return tmp_path, manifest, corpus, claim, text


def test_graph_recording_replays_without_network_or_approval(authored_corpus):
    root, manifest, corpus, claim, text = authored_corpus
    mock = MockProvider({"extract_evidence": {"findings": [{"quote": text,
                        "drug_ingredient": "metformin", "event_term": "diarrhoea"}]}}, model="authored")
    path = root / "recordings.agent.jsonl"
    recorder = RecordingProvider(mock, "authored", path)
    index = BM25(corpus)
    first = run_agent(claim=claim, index=index, manifest=manifest, provider=recorder, max_steps=3)
    with offline():
        second = predict(claim=claim, index=index, config={"recordings": str(root / "recordings.jsonl"),
                         "mode": "replay", "model": "authored", "max_documents": 50, "max_steps": 3})
    assert first.retrieved_ids == second.retrieved_ids == ["test-unit"]
    assert first.statements == second.statements
    assert second.assessment_status == "insufficient_evidence"
    assert second.abstained
    assert second.usage["human_approvals"] == second.usage["live_calls"] == 0
    assert second.usage["steps"] <= 3
    assert second.usage["llm_calls"] == 1
    assert second.usage["documents"] == 1
    assert not any(e["kind"] == "review_decision" for e in second.trace)


def test_missing_or_changed_recording_fails(authored_corpus):
    root, manifest, corpus, claim, _ = authored_corpus
    path = root / "empty.agent.jsonl"
    path.write_text("", encoding="utf-8")
    with offline(), pytest.raises(IntegrityError, match="Missing agent"):
        run_agent(claim=claim, index=BM25(corpus), manifest=manifest,
                  provider=RecordedProvider(path, "authored"), max_steps=2)
    path.write_text(json.dumps({"kind": "person3_provider_v1", "model": "authored",
                    "request_sha256": "bad", "request": {"model": "authored"},
                    "response": {"text": "{}"}}) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="hash/model"):
        RecordedProvider(path, "authored")


def test_recording_provider_resume_reuses_exact_calls_and_rejects_tampering(tmp_path):
    path = tmp_path / "resume.agent.jsonl"
    mock = MockProvider({"authored": {"result": "example"}}, model="authored")
    arguments = {"task": "authored", "system": "Authored offline test", "prompt": "first",
                 "json_schema": {}, "untrusted": "Authored snapshot"}
    first = RecordingProvider(mock, "authored", path)
    expected = first.complete(**arguments)
    prefix = path.read_bytes()
    resumed = RecordingProvider(mock, "authored", path, resume=True)
    assert resumed.complete(**arguments) == expected
    assert len(mock.calls) == 1 and resumed.actual_calls == 0
    resumed.complete(**{**arguments, "prompt": "second"})
    assert len(mock.calls) == 2 and resumed.actual_calls == 1
    assert path.read_bytes().startswith(prefix) and len(read_jsonl(path)) == 2
    with pytest.raises(IntegrityError, match="hash/model"):
        RecordingProvider(mock, "different-model", path, resume=True)
    rows = read_jsonl(path)
    rows[0]["request"]["prompt"] = "changed"
    dataset_module.write_rows(path, rows)
    with pytest.raises(IntegrityError, match="hash/model"):
        RecordingProvider(mock, "authored", path, resume=True)


def test_interrupted_batch_resumes_saved_claim_and_partial_calls(authored_corpus, monkeypatch):
    root, manifest, _, claim, _ = authored_corpus
    claims = [{"claim_id": f"authored-{i}", "split": "development", **claim,
               "claim_text": f"Authored claim {i}"} for i in range(2)]
    dataset_module.write_rows(root / "claims.jsonl", claims)
    data = json.loads(manifest.read_bytes())
    data.update(synthetic=False, annotation_status="independently_reviewed",
                claims_sha256=digest((root / "claims.jsonl").read_bytes()))
    dataset_module.write_json(manifest, data)
    mock = MockProvider({"authored_agent": {"example": "technical test"}, "single_shot_rag": {
        "retrieved_ids": ["E01"], "assessment_status": "insufficient_evidence", "abstained": True,
        "scope_mismatches": [], "contradictions": [], "statements": []}}, model="authored")
    interrupt = True
    def authored_agent(*, claim, provider, **kwargs):
        # Two calls, with interruption after the first saved response of claim 2.
        provider.complete(task="authored_agent", system="Authored", prompt=claim["claim_text"],
                          json_schema={}, untrusted="first")
        if interrupt and claim["claim_text"].endswith("1"):
            raise KeyboardInterrupt
        provider.complete(task="authored_agent", system="Authored", prompt=claim["claim_text"],
                          json_schema={}, untrusted="second")
        return Prediction(["test-unit"], assessment_status="insufficient_evidence", abstained=True,
                          statements=[], usage={"llm_calls": 2})
    monkeypatch.setattr(recording_module, "run_agent", authored_agent)
    with pytest.raises(KeyboardInterrupt):
        recording_module.record(root, "authored", "development", mock)
    previous_path = root / "recording-report-development.json"
    previous_bytes = previous_path.read_bytes()
    assert len(json.loads(previous_bytes)["claims"]) == 1
    agent_path = root / "recordings-development.agent.jsonl"
    prefix = agent_path.read_bytes()
    assert len(read_jsonl(agent_path)) == 3
    calls_before = len(mock.calls)
    interrupt = False
    assert recording_module.record(root, "authored", "development", mock, resume=True) == 0
    # Only missing second agent call and RAG for the unfinished claim cost calls.
    assert len(mock.calls) - calls_before == 2
    report = json.loads(previous_path.read_bytes())
    assert report["processed_claims"] == report["total_split_claims"] == 2
    assert report["claims"][0]["agent_recording"] == "cached_verified"
    assert report["claims"][0]["rag_recording"] == "cached"
    assert agent_path.read_bytes().startswith(prefix) and len(read_jsonl(agent_path)) == 4
    assert (root / "recording-history-development" / f"{digest(previous_bytes)}.json").read_bytes() == previous_bytes
    complete_bytes = previous_path.read_bytes()
    assert recording_module.record(root, "authored", "development", mock, resume=True) == 0
    assert len(mock.calls) - calls_before == 2
    # Budget mismatch is rejected before calling the model or rewriting progress.
    checkpoint = previous_path.read_bytes()
    with pytest.raises(IntegrityError, match="differs from the stopped run"):
        recording_module.record(root, "authored", "development", mock, resume=True, max_steps=3)
    assert previous_path.read_bytes() == checkpoint
    assert complete_bytes != b""


def test_resume_changed_claims_is_rejected_before_model_calls(authored_corpus):
    root, manifest, _, claim, _ = authored_corpus
    dataset_module.write_rows(root / "claims.jsonl", [{"claim_id": "example", "split": "development", **claim}])
    data = json.loads(manifest.read_bytes())
    data.update(synthetic=False, annotation_status="independently_reviewed", claims_sha256="stale")
    dataset_module.write_json(manifest, data)
    mock = MockProvider({})
    with pytest.raises(IntegrityError, match="Claims changed"):
        recording_module.record(root, "authored", "development", mock, resume=True)
    assert mock.calls == []


def test_normalization_checkpoint_uses_no_model(authored_corpus):
    _, manifest, corpus, claim, _ = authored_corpus
    claim = {**claim, "drug": "UnknownBrandForTest"}
    provider = MockProvider({})
    result = run_agent(claim=claim, index=BM25(corpus), manifest=manifest, provider=provider)
    assert result.assessment_status == "requires_human_review"
    assert result.abstained
    assert result.retrieved_ids == []
    assert result.usage["llm_calls"] == 0
    assert provider.calls == []


def test_model_quote_does_not_match_source_is_excluded(authored_corpus):
    _, manifest, corpus, claim, _ = authored_corpus
    provider = MockProvider({"extract_evidence": {"findings": [{"quote": "Fabricated quotation",
                             "drug_ingredient": "metformin", "event_term": "diarrhoea"}]}})
    result = run_agent(claim=claim, index=BM25(corpus), manifest=manifest, provider=provider, max_steps=2)
    assert result.statements == []
    assert result.assessment_status == "insufficient_evidence"


def test_span_mapping_rejects_outside_corpus(authored_corpus):
    _, _, corpus, _, text = authored_corpus
    assert covering_units(corpus, "test-doc", 0, len(text)) == ["test-unit"]
    with pytest.raises(IntegrityError):
        covering_units(corpus, "test-doc", 0, len(text) + 10)


def test_reviewer_agreement_never_turns_missing_labels_into_perfect_score():
    assert agreement_summary([])["cohen_kappa"] is None
    assert agreement_summary([])["agreement"] is None
    assert agreement_summary([("same", "same")])["cohen_kappa"] is None
    checked = agreement_summary([("yes", "yes"), ("no", "no"), ("yes", "no"), ("no", "yes")])
    assert checked["agreement"] == 0.5
    assert checked["cohen_kappa"] == 0.0


def test_expert_span_maps_to_units_without_manufacturing_more_gold(authored_corpus):
    _, _, corpus, _, text = authored_corpus
    row = {"claim_id": "authored-test", "evidence_annotations": [{"evidence_id": "expert-local-id",
           "document_id": "test-doc", "span_locator": {"start": 0, "end": len(text)},
           "scope_fields": [{"field": "route", "outcome": "mismatched"}]}],
           "required_gold_evidence_ids": [], "optional_gold_evidence_ids": ["expert-local-id"],
           "contradiction_annotations": [], "expected_assessment_status": "scope_mismatch",
           "expected_abstention": True}
    result = convert_annotation(row, corpus)
    assert result["required_evidence_ids"] == []
    assert result["relevant_evidence_ids"] == ["test-unit"]
    assert result["scope_mismatches"] == ["test-unit:route"]
    assert result["assessment_status"] == "scope_mismatch"


def test_publication_requires_explicit_pinned_adjudication(tmp_path, monkeypatch):
    # All identities/labels in this test are authored examples, stored only in tmp_path.
    module = dataset_module

    doc = SourceDocument(doc_id="authored-doc", source="pubmed", source_id="authored-source", version=1,
                         text="Authored technical example.", hash=digest(b"Authored technical example."),
                         retrieved_at="2026-10-02T10:00:00+00:00")
    candidate = SimpleNamespace(bundle_hash="authored-bundle-hash", documents=[doc])
    monkeypatch.setattr(module, "load_candidate_corpus", lambda path: candidate)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    dictionary = tmp_path / "data/dictionaries/mvp_candidates_2026_10_02.json"
    dictionary.parent.mkdir(parents=True)
    dictionary.write_text(json.dumps({"version": "authored-test", "corpus_sha256": candidate.bundle_hash}), encoding="utf-8")
    bench = tmp_path / "bench"
    bench.mkdir()
    claim = {"claim_id": "authored-claim", "version": 1, "family_id": "authored-family", "split": "development",
             "claim": {"claim_text": "Authored claim", "drug": "AuthoredDrug", "event": "AuthoredEvent"},
             "source_doc_ids": [doc.doc_id]}
    (bench / "mvp_manifest.json").write_text(json.dumps({"corpus_sha256": candidate.bundle_hash,
                  "corpus_cutoff": "2026-10-02T10:00:00+00:00"}), encoding="utf-8")
    module.write_rows(bench / "mvp_claims.jsonl", [claim])
    row = {"claim_id": claim["claim_id"], "claim_version": 1, "family_id": claim["family_id"],
           "split": "development", "source_manifest_sha256": candidate.bundle_hash,
           "record_status": "completed_independent_expert_review", "annotator_role": "clinical_pharmacist",
           "annotation_timestamp": "2026-10-02T12:00:00Z", "expected_assessment_status": "insufficient_evidence",
           "expected_abstention": True, "evidence_annotations": [], "contradiction_annotations": [],
           "required_gold_evidence_ids": [], "optional_gold_evidence_ids": [], "critical_gaps": ["Authored example"]}
    for slot in ("reviewer_a", "reviewer_b"):
        module.write_rows(bench / f"{slot}.jsonl", [{**row, "annotator_id": f"authored-{slot}"}])
    module.export_dataset(tmp_path / "unused.zip", bench, tmp_path / "packet")
    approval = json.loads((tmp_path / "packet/freeze_approval.template.json").read_text(encoding="utf-8"))
    approval.update(adjudicator_id="authored-adjudicator", adjudicator_role="clinical_pharmacist",
                    approved_at="2026-10-02T13:00:00Z", reason="Authored unit-test resolution", final_annotations=[{
                        **row, "annotator_id": "authored-adjudicator", "adjudication": {"status": "resolved",
                        "adjudicator_id": "authored-adjudicator", "resolution_reason": "Authored resolution"}}])
    approval_path = tmp_path / "approval.json"
    module.write_json(approval_path, approval)
    result = module.export_dataset(tmp_path / "unused.zip", bench, tmp_path / "frozen", approval=approval_path)
    assert result["clinical_metrics_ready"]
    assert read_jsonl(tmp_path / "frozen/annotations.jsonl")[0]["assessment_status"] == "insufficient_evidence"
    manifest = json.loads((tmp_path / "frozen/corpus_manifest.json").read_text(encoding="utf-8"))
    assert manifest["annotation_status"] == "independently_reviewed"
    approval["input_sha256"]["reviewer_a.jsonl"] = "stale"
    module.write_json(approval_path, approval)
    with pytest.raises(IntegrityError, match="pin all reviewed"):
        module.export_dataset(tmp_path / "unused.zip", bench, tmp_path / "rejected-stale", approval=approval_path)
    assert not (tmp_path / "rejected-stale/annotations.jsonl").exists()
