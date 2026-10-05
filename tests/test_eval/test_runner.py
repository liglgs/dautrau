import json
from dataclasses import replace

import pytest

from eval.corpus import IntegrityError, digest
from eval.run_evaluation import EvaluationConfig, run_evaluation
from scripts.seed_demo import MODEL, build


@pytest.fixture
def config(tmp_path):
    build(tmp_path)
    return EvaluationConfig(
        manifest=tmp_path / "corpus_manifest.json",
        claims=tmp_path / "claims.jsonl",
        annotations=tmp_path / "annotations.jsonl",
        recordings=tmp_path / "recordings.jsonl",
        allow_synthetic=True,
        model=MODEL,
        output=tmp_path / "results",
    )


def test_python_entrypoint_writes_auditable_report_from_other_directory(config, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_evaluation(config)
    assert result.exit_code == 1
    assert len(result.rows) == 12 and result.errors == 4
    assert result.summaries["keyword"]["successful"] == 4
    assert json.loads((result.output / "aggregate.json").read_text(encoding="utf-8")) == result.summaries
    assert (result.output / "report.md").read_text(encoding="utf-8") == result.markdown
    assert result.manifest["claims_sha256"] == digest(config.claims.read_bytes())
    assert "eval/run_evaluation.py" in result.manifest["code_sha256"]
    assert all("\\" not in path for path in result.manifest["code_sha256"])
    assert all(row["prediction"]["usage"]["queries"] == 1 for row in result.rows if row["system"] == "single_shot_rag")


@pytest.mark.parametrize("failure", ["missing", "invalid_json", "model_mismatch"])
def test_bad_recordings_are_rag_errors_and_do_not_abort_keyword(config, failure):
    if failure == "missing":
        config = replace(config, recordings=config.output.parent / "missing.jsonl")
    elif failure == "invalid_json":
        config.recordings.write_text("{broken}\n", encoding="utf-8")
    else:
        config = replace(config, model="wrong-model")
    result = run_evaluation(config)
    assert result.errors == 8 and len(result.rows) == 12
    assert result.summaries["keyword"]["successful"] == 4
    rag_rows = [row for row in result.rows if row["system"] == "single_shot_rag"]
    assert all("Synthesis recording unavailable" in row["error"]["message"] for row in rag_rows)
    assert all("metrics" not in row for row in rag_rows)
    assert len((result.output / "per-claim.jsonl").read_text(encoding="utf-8").splitlines()) == 12


def test_keyword_does_not_load_unrelated_recordings(config):
    config.recordings.write_text("{broken}\n", encoding="utf-8")
    result = run_evaluation(replace(config, system="keyword"))
    assert result.errors == 0 and result.exit_code == 0
    assert all(row["prediction"]["statements"] is None for row in result.rows)


def test_python_entrypoint_requires_synthetic_opt_in(config):
    with pytest.raises(IntegrityError, match="requires --allow-synthetic"):
        run_evaluation(replace(config, allow_synthetic=False))
    assert not config.output.exists()


@pytest.mark.parametrize(
    "override", [{"mode": "live"}, {"max_documents": True}, {"max_steps": 1.2}, {"max_documents": 101}]
)
def test_invalid_configuration_fails_before_writing_report(config, override):
    with pytest.raises(ValueError):
        run_evaluation(replace(config, **override))
    assert not config.output.exists()
