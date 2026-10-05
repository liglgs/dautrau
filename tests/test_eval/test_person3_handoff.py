import json
import shutil
from pathlib import Path

from eval.corpus import digest
from eval.person3_handoff import inspect_handoff

ROOT = Path(__file__).resolve().parents[2]


def handoff(tmp_path):
    target = tmp_path / "benchmark"
    shutil.copytree(ROOT / "data/benchmark", target)
    return target


def test_draft_handoff_never_becomes_clinical_metrics(tmp_path):
    report = inspect_handoff(handoff(tmp_path), tmp_path / "missing.zip")
    assert report["claims"] == 20
    assert report["split_counts"] == {"development": 5, "heldout": 15}
    assert report["gold_rows"] == 0
    assert report["completed_reviews"] == {"reviewer_a": 0, "reviewer_b": 0}
    assert report["clinical_metrics_ready"] is False
    assert report["metrics"] is None
    assert report["candidate_corpus_valid"] is False
    assert any("bundle is missing" in issue for issue in report["blockers"])


def test_checks_split_leakage_instead_of_trusting_manifest_flag(tmp_path):
    folder = handoff(tmp_path)
    path = folder / "mvp_claims.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[-1]["family_id"] = rows[0]["family_id"]
    rows[-1]["source_doc_ids"] = rows[0]["source_doc_ids"]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    report = inspect_handoff(folder, tmp_path / "missing.zip")
    assert any("families overlap" in issue for issue in report["blockers"])
    assert any("documents overlap" in issue for issue in report["blockers"])


def test_rejects_changed_or_corrupt_source_bundle(tmp_path):
    folder = handoff(tmp_path)
    bundle = tmp_path / "corrupt.zip"
    bundle.write_bytes(b"not a source archive")
    report = inspect_handoff(folder, bundle)
    assert any("SHA-256 disagrees" in issue for issue in report["blockers"])
    manifest = folder / "mvp_manifest.json"
    value = json.loads(manifest.read_text())
    value["corpus_sha256"] = digest(bundle.read_bytes())
    manifest.write_text(json.dumps(value), encoding="utf-8")
    report = inspect_handoff(folder, bundle)
    assert report["candidate_corpus_valid"] is False
    assert any("Invalid handoff" in issue for issue in report["blockers"])


def test_missing_packet_is_a_reported_blocker(tmp_path):
    report = inspect_handoff(tmp_path, tmp_path / "missing.zip")
    assert report["clinical_metrics_ready"] is False
    assert len(report["blockers"]) == 5
