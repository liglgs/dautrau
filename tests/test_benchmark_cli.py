"""The benchmark refuses missing credentials and writes explicit partial runs."""

import json
from threading import Barrier

import pytest

from research.fixtures import load_cases
from research.run_benchmark import execute, require_model_key
from src.ai.transport import ModelResult
from src.config import Settings
from src.vmec import DomainError


def test_missing_key_fails_before_adapter_call():
    settings = Settings(_env_file=None, model_provider="openai", openai_api_key="")
    with pytest.raises(DomainError) as error:
        require_model_key(settings)
    assert error.value.code == "MODEL_UNAVAILABLE"


def test_call_cap_writes_incomplete_manifest_and_rows(tmp_path):
    calls = []

    def adapter(system, user):
        calls.append((system, user))
        return ModelResult({"assertions": []}, "fixture", "fixture", "fixture", 2, 1, 3)

    settings = Settings(_env_file=None, model_provider="openai", openai_api_key="test-key", model_name="fixture")
    summary = execute(load_cases("dev")[:2], ["B2"], tmp_path, adapter, settings, max_calls=1)
    assert len(calls) == 1
    assert summary["status"] == "incomplete"
    manifest = json.loads((tmp_path / "vmec03-manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "incomplete"
    rows = [json.loads(line) for line in (tmp_path / "vmec03-per-case.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert all(row["status"] == "incomplete" for row in rows)
    assert "test-key" not in (tmp_path / "vmec03-manifest.json").read_text(encoding="utf-8")


def test_priced_cost_cap_stops_before_next_call(tmp_path):
    calls = []

    def adapter(system, user):
        calls.append(user)
        return ModelResult({"assertions": []}, "fixture", "fixture", "fixture", 2, 1, 3)

    settings = Settings(_env_file=None, model_provider="openai", openai_api_key="test-key",
                        model_input_usd_per_million=1_000_000, model_output_usd_per_million=1_000_000)
    summary = execute(load_cases("dev")[:1], ["B2"], tmp_path, adapter, settings, max_cost_usd=1)
    assert len(calls) == 1
    assert summary["status"] == "incomplete"
    manifest = json.loads((tmp_path / "vmec03-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cost_usd"] == 3


def test_parallel_cases_keep_stable_rows_and_accounting(tmp_path):
    rendezvous = Barrier(2, timeout=5)

    def adapter(_system, _user):
        rendezvous.wait()
        return ModelResult({"assertions": [], "issues": [], "actions": []},
                           "fixture", "fixture", "fixture-returned", 2, 1, 3)

    settings = Settings(_env_file=None, model_provider="openai", openai_api_key="test-key")
    summary = execute(load_cases("dev")[:2], ["B1"], tmp_path, adapter, settings, workers=2)
    assert summary["status"] == "completed"
    assert summary["attempts"] == 2
    rows = [json.loads(line) for line in (tmp_path / "vmec03-per-case.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["case_id"] for row in rows] == ["DEV-01", "DEV-02"]
    manifest = json.loads((tmp_path / "vmec03-manifest.json").read_text(encoding="utf-8"))
    assert manifest["workers"] == 2
    assert manifest["returned_models"] == ["fixture-returned"]
