"""Kiểm thử bộ dựng chuẩn vàng giai đoạn 1 và tính toàn vẹn của tệp đã commit.

Không bài nào gọi mạng: phần khớp nhãn kiểm thử bằng nhãn giả lập, phần tệp dữ liệu
kiểm thử bằng chính tệp đã commit và băm trong manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.gold import build_gold_dataset as gold

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "data" / "gold" / "spec.json"
DATASET_PATH = ROOT / "data" / "gold" / "drug-event-pairs.jsonl"
MANIFEST_PATH = ROOT / "data" / "gold" / "manifest.json"


@pytest.fixture(scope="module")
def spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ khớp chuỗi
def test_find_term_treats_whitespace_between_words_as_a_separator() -> None:
    assert gold.find_term("Risk of Gastrointestinal Bleeding was reported", "gastrointestinal bleeding")
    assert gold.find_term("gastrointestinal   bleeding occurred", "gastrointestinal bleeding")
    assert gold.find_term("gastrointestinal-bleeding occurred", "gastrointestinal bleeding")


def test_find_term_keeps_hyphens_inside_a_word_literal() -> None:
    """Gạch nối trong một từ là ký tự thật: spec phải khai báo riêng biến thể.

    Vì vậy sự kiện tiêu hóa có cả 'gastrointestinal haemorrhage' và
    'gastro-intestinal haemorrhage', còn Stevens-Johnson có cả hai kiểu viết.
    """
    assert gold.find_term("Stevens-Johnson Syndrome was reported", "stevens-johnson syndrome")
    assert gold.find_term("Stevens Johnson Syndrome was reported", "stevens johnson syndrome")
    assert gold.find_term("gastro-intestinal haemorrhage occurred", "gastro-intestinal haemorrhage")
    assert gold.find_term("Stevens Johnson Syndrome was reported", "stevens-johnson syndrome") is None
    assert gold.find_term("gastro-intestinal haemorrhage occurred", "gastrointestinal haemorrhage") is None


def test_find_term_does_not_match_inside_a_longer_word() -> None:
    assert gold.find_term("hepatotoxicities were observed", "hepatotoxicity") is None
    assert gold.find_term("hyperangioedema-like", "angioedema") is None


def test_quote_around_returns_the_containing_sentence_and_respects_limit() -> None:
    text = "First sentence. The patient developed rhabdomyolysis after treatment. Third sentence."
    match = gold.find_term(text, "rhabdomyolysis")
    assert match is not None
    assert (
        gold.quote_around(text, match.start(), match.end()) == "The patient developed rhabdomyolysis after treatment."
    )
    long_text = "A" * 500 + " pancreatitis " + "B" * 500
    match = gold.find_term(long_text, "pancreatitis")
    assert match is not None
    assert len(gold.quote_around(long_text, match.start(), match.end(), max_chars=120)) <= 120


def test_match_any_reports_the_synonym_that_matched() -> None:
    hit = gold.match_any(
        "Cases of acute renal failure have been reported.", ["acute kidney injury", "acute renal failure"]
    )
    assert hit is not None
    assert hit[0] == "acute renal failure"
    assert hit[1] == "Cases of acute renal failure have been reported."


# ------------------------------------------------------------------ chọn nhãn
def test_select_label_prefers_newest_effective_time() -> None:
    labels = [
        {"set_id": "b", "effective_time": "20240101"},
        {"set_id": "a", "effective_time": "20250101"},
        {"set_id": "c", "effective_time": "20250101"},
    ]
    assert gold.select_label(labels)["set_id"] == "a"


def test_select_label_ignores_entries_without_set_id() -> None:
    assert (
        gold.select_label([{"effective_time": "20250101"}, {"set_id": "z", "effective_time": "20200101"}])["set_id"]
        == "z"
    )
    assert gold.select_label([]) is None


def test_select_label_prefers_single_ingredient_labels() -> None:
    labels = [
        {
            "set_id": "combo",
            "effective_time": "20260101",
            "openfda": {"generic_name": ["ASPIRIN AND EXTENDED-RELEASE DIPYRIDAMOLE"]},
        },
        {"set_id": "single", "effective_time": "20250101", "openfda": {"generic_name": ["ASPIRIN"]}},
    ]
    assert gold.select_label(labels, "aspirin")["set_id"] == "single"
    # Không có nhãn một hoạt chất thì dùng nhãn phối hợp, và tên nhãn vẫn được ghi lại.
    combo_only = [labels[0]]
    assert gold.select_label(combo_only, "aspirin")["set_id"] == "combo"


def test_is_single_ingredient_accepts_salt_forms_and_rejects_combinations() -> None:
    assert gold.is_single_ingredient({"openfda": {"generic_name": ["AMLODIPINE BESYLATE"]}}, "amlodipine")
    assert gold.is_single_ingredient({"openfda": {"generic_name": ["VALPROIC ACID"]}}, "valproic acid")
    assert not gold.is_single_ingredient({"openfda": {"generic_name": ["IBUPROFEN AND FAMOTIDINE"]}}, "ibuprofen")
    assert not gold.is_single_ingredient(
        {"openfda": {"generic_name": ["REDICARE NON-ASPIRIN, ACETAMINOPHEN 500MG"]}}, "aspirin"
    )
    assert not gold.is_single_ingredient({"openfda": {}}, "aspirin")


def test_section_texts_joins_lists_and_skips_empty_sections() -> None:
    label = {"adverse_reactions": ["First.", "Second."], "warnings": [], "contraindications": "None."}
    texts = gold.section_texts(label, ["adverse_reactions", "warnings", "contraindications", "boxed_warning"])
    assert texts == {"adverse_reactions": "First.\nSecond.", "contraindications": "None."}


# ------------------------------------------------------------------ dựng bản ghi
def _drug() -> dict:
    return {"index": 4, "generic_name": "aspirin", "vn_name": "acid acetylsalicylic", "drug_class": "NSAID"}


def _event() -> dict:
    return {
        "index": 1,
        "name": "Gastrointestinal haemorrhage",
        "slug": "gastrointestinal-haemorrhage",
        "meddra_pt": "GASTROINTESTINAL HAEMORRHAGE",
        "synonyms": ["gastrointestinal bleeding"],
    }


def _pair(spec: dict, label: dict | None, **overrides) -> dict:
    kwargs = dict(
        spec=spec,
        drug=_drug(),
        event=_event(),
        label=label,
        label_error=None,
        label_status=200,
        drug_total=100,
        drug_status=200,
        event_total=7,
        event_status=200,
        term_observed=True,
        retrieved_at="2026-10-06T00:00:00+00:00",
        label_retrieved_at="2026-10-06T00:00:00+00:00",
    )
    kwargs.update(overrides)
    return gold.build_pair(**kwargs)


def test_build_pair_marks_a_listed_event_with_section_term_and_quote(spec: dict) -> None:
    label = {
        "set_id": "set-1",
        "version": "3",
        "effective_time": "20250101",
        "openfda": {"generic_name": ["ASPIRIN"], "brand_name": ["BAYER"]},
        "adverse_reactions": ["Gastrointestinal bleeding has been reported."],
    }
    record = _pair(spec, label)
    evidence = record["label_evidence"]
    assert record["gold_label"] == "label_listed"
    assert evidence["status"] == "listed"
    assert evidence["matched_section"] == "adverse_reactions"
    assert evidence["matched_term"] == "gastrointestinal bleeding"
    assert evidence["matched_quote"] == "Gastrointestinal bleeding has been reported."
    assert evidence["label_url"].endswith("setid=set-1")
    # Hoạt chất ở vị trí 4 (chỉ số 0-based 3) rơi vào tập test theo quy tắc chia trong spec.
    assert record["split"] == "test"
    assert record["review"]["status"] == "candidate_not_gold"


def test_build_pair_marks_absence_in_checked_sections_as_not_listed(spec: dict) -> None:
    label = {"set_id": "set-2", "effective_time": "20250101", "adverse_reactions": ["Headache and nausea."]}
    record = _pair(spec, label)
    assert record["label_evidence"]["status"] == "not_listed"
    assert record["gold_label"] == "label_not_listed"
    assert record["label_evidence"]["matched_quote"] is None


def test_build_pair_distinguishes_no_section_from_no_label(spec: dict) -> None:
    no_section = _pair(
        spec, {"set_id": "set-3", "effective_time": "20250101", "dosage_and_administration": ["Take once."]}
    )
    assert no_section["label_evidence"]["status"] == "no_section"
    assert no_section["gold_label"] == "label_not_listed"
    missing = _pair(spec, None, label_error="http_404: openFDA không có nhãn khớp truy vấn", label_status=404)
    assert missing["label_evidence"]["status"] == "no_label"
    assert missing["gold_label"] is None


def test_build_pair_records_faers_404_as_zero_with_a_note(spec: dict) -> None:
    record = _pair(
        spec,
        {"set_id": "set-4", "effective_time": "20250101", "warnings": ["Bleeding risk."]},
        event_total=0,
        event_status=404,
        term_observed=None,
    )
    faers = record["faers_reports"]
    assert faers["reports_drug_and_event"] == 0
    assert faers["term_observed"] is None
    assert faers["no_result_note"].startswith("openFDA trả HTTP 404")
    assert faers["pair_query_http_status"] == 404


# ------------------------------------------------------------------ toàn vẹn tệp đã commit
def test_dataset_file_matches_its_manifest_hash(manifest: dict) -> None:
    payload = DATASET_PATH.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == manifest["dataset_sha256"]
    assert manifest["spec_sha256"] == hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()


def test_manifest_counts_match_the_dataset(records: list[dict], manifest: dict) -> None:
    counts = manifest["counts"]
    assert counts["pairs_total"] == len(records)
    recomputed: dict[str, int] = {}
    for record in records:
        status = record["label_evidence"]["status"]
        recomputed[status] = recomputed.get(status, 0) + 1
    assert counts["label_listed"] == recomputed.get("listed", 0)
    assert counts["label_not_listed"] == recomputed.get("not_listed", 0) + recomputed.get("no_section", 0)
    assert counts["no_label"] == recomputed.get("no_label", 0)
    assert counts["per_status"] == recomputed


def test_dataset_covers_the_planned_matrix(records: list[dict], spec: dict) -> None:
    assert len(records) == len(spec["drugs"]) * len(spec["events"]) == 300
    assert len({record["pair_id"] for record in records}) == len(records)
    assert {record["drug"] for record in records} == {drug["generic_name"] for drug in spec["drugs"]}
    assert {record["event_slug"] for record in records} == {event["slug"] for event in spec["events"]}


def test_every_record_is_a_candidate_with_provenance(records: list[dict], spec: dict) -> None:
    checked = set(spec["label_rule"]["checked_sections"])
    for record in records:
        assert record["review"]["status"] == "candidate_not_gold"
        assert record["review"]["reviewer_id"] is None
        assert record["limitations"]
        assert record["gold_basis"] == gold.METHOD_VERSION
        assert set(record["label_evidence"]["checked_sections"]) == checked
        evidence = record["label_evidence"]
        if evidence["status"] == "listed":
            assert evidence["matched_quote"] and evidence["matched_term"] and evidence["label_url"]
            assert evidence["matched_section"] in checked
            assert record["gold_label"] == "label_listed"
        elif evidence["status"] in {"not_listed", "no_section"}:
            assert record["gold_label"] == "label_not_listed"
            assert evidence["label_url"] is not None
        else:
            assert evidence["status"] == "no_label"
            assert record["gold_label"] is None
            assert evidence["error"]


def test_split_keeps_drugs_apart_and_covers_both_sides(records: list[dict]) -> None:
    by_split: dict[str, set[str]] = {}
    for record in records:
        assert record["split"] in {"development", "test"}
        by_split.setdefault(record["split"], set()).add(record["drug"])
    assert by_split["development"] and by_split["test"]
    assert not by_split["development"] & by_split["test"]


def test_manifest_declares_sources_licences_and_limitations(manifest: dict) -> None:
    assert manifest["status"] == "candidate_not_gold"
    assert manifest["review"]["approved_by"] is None
    assert {source["id"] for source in manifest["sources"]} == {"openfda_label", "openfda_event"}
    for source in manifest["sources"]:
        assert source["licence"] and source["url"].startswith("https://api.fda.gov/")
    assert any("không phải bằng chứng nhân quả" in line for line in manifest["limitations"])
    assert manifest["raw_snapshots"]["committed"] is False
