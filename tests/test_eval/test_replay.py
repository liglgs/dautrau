import json
import socket

import pytest

from eval.baselines.keyword import BM25
from eval.baselines.single_shot_rag import RecordedSynthesis, run
from eval.contracts import Prediction
from eval.corpus import Corpus, IntegrityError, read_jsonl
from eval.run_evaluation import evaluate, offline, validate_dataset
from scripts.seed_demo import MODEL, build


@pytest.fixture
def dataset(tmp_path):
    build(tmp_path)
    return tmp_path, Corpus.load(tmp_path / "corpus_manifest.json")


def test_replay_never_opens_network():
    with offline(), pytest.raises(RuntimeError, match="Network disabled"):
        socket.create_connection(("example.org", 443))


def test_replay_blocks_udp_without_dns():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        with offline(), pytest.raises(RuntimeError, match="Network disabled"):
            connection.sendto(b"not sent", ("127.0.0.1", 9))


def test_snapshot_hash_tampering_fails(dataset):
    path, _ = dataset
    (path / "snapshots/broad-doc-1.txt").write_text("tampered")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        Corpus.load(path / "corpus_manifest.json")


def test_future_document_rejected(dataset):
    path, _ = dataset
    manifest = json.loads((path / "corpus_manifest.json").read_text())
    manifest["documents"][0]["available_at"] = "2027-01-01T00:00:00Z"
    (path / "corpus_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(IntegrityError, match="Future document"):
        Corpus.load(path / "corpus_manifest.json")


def test_locator_must_match_exact_span(dataset):
    path, _ = dataset
    manifest = json.loads((path / "corpus_manifest.json").read_text())
    manifest["documents"][0]["units"][0]["start"] = 1
    (path / "corpus_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(IntegrityError, match="locator"):
        Corpus.load(path / "corpus_manifest.json")


def test_split_family_leakage_rejected(dataset):
    path, corpus = dataset
    claims = read_jsonl(path / "claims.jsonl")
    claims[-1]["family_id"] = claims[0]["family_id"]
    with pytest.raises(IntegrityError, match="family overlaps"):
        validate_dataset(claims, read_jsonl(path / "annotations.jsonl"), corpus)


def test_foreign_citation_rejected():
    with pytest.raises(ValueError, match="outside retrieved"):
        Prediction.parse(
            {"retrieved_ids": ["a"], "statements": [{"kind": "fact", "text": "x", "evidence_ids": ["foreign"]}]},
            # Visible in the frozen corpus is not enough: it must have been retrieved.
            allowed_ids={"a", "foreign"},
        )


def test_gold_does_not_enter_synthesis(dataset):
    path, corpus = dataset
    claims = read_jsonl(path / "claims.jsonl")
    claims[0]["private_gold_canary"] = "never send to model"
    rows = evaluate(
        corpus=corpus,
        claims=claims,
        annotations=read_jsonl(path / "annotations.jsonl"),
        system="single_shot_rag",
        split="development",
        model=MODEL,
        recordings=path / "recordings.jsonl",
    )
    assert all(row["error"] is None for row in rows)
    assert rows[0]["prediction"]["usage"]["live_calls"] == 0


def test_missing_agent_is_explicit_error(dataset):
    path, corpus = dataset
    rows = evaluate(
        corpus=corpus,
        claims=read_jsonl(path / "claims.jsonl"),
        annotations=read_jsonl(path / "annotations.jsonl"),
        system="agent",
        split="development",
        model=MODEL,
    )
    assert all("Agent integration missing" in row["error"]["message"] for row in rows)
    assert all("metrics" not in row for row in rows)


def test_missing_recording_does_not_fallback(dataset):
    path, corpus = dataset
    synthesis = RecordedSynthesis(path / "recordings.jsonl", model=MODEL)
    with pytest.raises(ValueError, match="Missing synthesis recording"):
        run(BM25(corpus), {"drug": "other", "event": "unknown"}, synthesis)
