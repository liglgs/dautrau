"""Kiểm thử bộ phân tích ELT: phân tích nguồn, kiểm chứng băm và hồi quy hoạt chất DailyMed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.elt.parse import (
    dailymed_index_entries,
    parse_dailymed_xml,
    parse_faers_json,
    parse_pubmed_xml,
)

SPL_WITH_TWO_INGREDIENT_CLASSES = """<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="urn:hl7-org:v3">
  <setId root="11111111-2222-3333-4444-555555555555"/>
  <versionNumber value="7"/>
  <effectiveTime value="20240101"/>
  <title>IBUPROFEN TABLET</title>
  <manufacturedProduct>
    <ingredient classCode="ACTIB">
      <ingredientSubstance><name>IBUPROFEN</name></ingredientSubstance>
    </ingredient>
    <ingredient classCode="ACTIM">
      <ingredientSubstance><name>IBUPROFEN</name></ingredientSubstance>
    </ingredient>
    <routeCode code="C38288" displayName="ORAL"/>
  </manufacturedProduct>
  <component><section><title>INDICATIONS AND USAGE</title><text>Đau nhẹ.</text></section></component>
  <component><section><title>WARNINGS</title><text>Cảnh báo chung.</text></section></component>
  <component><section><title>DOSAGE AND ADMINISTRATION</title><text>200 mg mỗi 6 giờ.</text></section></component>
</document>
"""

FAERS_PAYLOAD = {
    "meta": {"results": {"total": 1}},
    "results": [
        {
            "safetyreportid": "10006463",
            "receivedate": "20180102",
            "serious": "1",
            "occurcountry": "US",
            "primarysource": {"reportercountry": "COUNTRY NOT SPECIFIED"},
            "patient": {
                "patientonsetage": "54",
                "patientonsetageunit": "801",
                "patientsex": "2",
                "drug": [
                    {"medicinalproduct": "IBUPROFEN", "drugcharacterization": "1", "openfda": {"generic_name": "IBUPROFEN"}},
                    {"medicinalproduct": "ASPIRIN", "drugcharacterization": "2"},
                ],
                "reaction": [{"reactionmeddrapt": "GASTROINTESTINAL HAEMORRHAGE"}],
            },
        }
    ],
}

PUBMED_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>39466269</PMID>
      <Article>
        <Journal><Title>JAMA</Title><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal>
        <ArticleTitle>Peptic Ulcer Disease: A Review.</ArticleTitle>
        <Abstract><AbstractText>Tóm tắt kiểm thử.</AbstractText></Abstract>
        <PublicationTypeList><PublicationType>Review</PublicationType></PublicationTypeList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">39466269</ArticleId>
        <ArticleId IdType="doi">10.1001/jama.2024.19094</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_dailymed_ingredients_cover_active_and_moiety_classes(tmp_path: Path) -> None:
    """Hồi quy: hoạt chất nằm trong lớp ACTIB/ACTIM, không phải đường dẫn XPath cũ."""
    doc = parse_dailymed_xml(
        SPL_WITH_TWO_INGREDIENT_CLASSES.encode("utf-8"),
        pair_id="ibuprofen__gastrointestinal-haemorrhage",
        raw_path=str(tmp_path / "spl.xml"),
        expected_setid="11111111-2222-3333-4444-555555555555",
    )
    assert doc.structured["ingredients"] == ["IBUPROFEN"]
    assert doc.structured["single_ingredient"] is True
    assert doc.structured["routes"] == ["ORAL"]
    assert doc.structured["n_sections"] == 3
    assert doc.doc_id == "dailymed:11111111-2222-3333-4444-555555555555:7"
    assert "INDICATIONS AND USAGE" in doc.text


def test_dailymed_setid_mismatch_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SETID"):
        parse_dailymed_xml(
            SPL_WITH_TWO_INGREDIENT_CLASSES.encode("utf-8"),
            pair_id=None,
            raw_path=str(tmp_path / "spl.xml"),
            expected_setid="ffffffff-0000-0000-0000-000000000000",
        )


def test_dailymed_index_entries_reads_spls_payload() -> None:
    payload = {"data": [{"setid": "abc", "title": "Nhãn A", "published_date": "2024-01-01"}]}
    entries = dailymed_index_entries(json.dumps(payload).encode("utf-8"))
    assert entries[0]["setid"] == "abc"
    assert entries[0]["title"] == "Nhãn A"
    assert entries[0]["published_date"] == "2024-01-01"


def test_faers_report_is_normalised_with_stable_doc_id(tmp_path: Path) -> None:
    docs = parse_faers_json(
        json.dumps(FAERS_PAYLOAD).encode("utf-8"),
        pair_id="ibuprofen__gastrointestinal-haemorrhage",
        raw_path=str(tmp_path / "faers.json"),
        drug="ibuprofen",
    )
    assert len(docs) == 1
    doc = docs[0]
    assert doc.doc_id == "faers:10006463:1"
    assert doc.structured["n_drugs"] == 2
    assert doc.structured["n_reactions"] == 1
    assert doc.structured["reporter_country"] == "COUNTRY NOT SPECIFIED"
    assert doc.content_level == "spontaneous_report"
    # Văn bản chuẩn hoá phải ổn định: sắp xếp khoá nên băm không đổi giữa các lần chạy.
    again = parse_faers_json(
        json.dumps(FAERS_PAYLOAD).encode("utf-8"),
        pair_id="ibuprofen__gastrointestinal-haemorrhage",
        raw_path=str(tmp_path / "faers.json"),
        drug="ibuprofen",
    )[0]
    assert again.text_sha256 == doc.text_sha256


def test_pubmed_parsing_keeps_abstract_and_doi(tmp_path: Path) -> None:
    docs = parse_pubmed_xml(PUBMED_XML.encode("utf-8"), pair_id="ibuprofen__gastrointestinal-haemorrhage",
                            raw_path=str(tmp_path / "pubmed.xml"))
    assert len(docs) == 1
    doc = docs[0]
    assert doc.doc_id == "pubmed:39466269:1"
    assert doc.structured["has_abstract"] is True
    assert doc.structured["doi"] == ["10.1001/jama.2024.19094"]
    assert doc.content_level == "abstract_only"


BUNDLE = Path("data/mvp-candidates-50-2026-10-02")
bundle_missing = not BUNDLE.exists()


@pytest.mark.skipif(bundle_missing, reason="gói 50 mẫu chưa được tải (data/mvp-candidates-50-2026-10-02)")
def test_bundle_text_hashes_match_released_json() -> None:
    """Kiểm chứng hai chiều: phân tích lại tệp thô phải cho đúng băm đã phát hành."""
    from scripts.elt.run_elt import parse_bundle

    from scripts.elt import config
    from scripts.elt.manifest import RunManifest

    docs, summary = parse_bundle(RunManifest(run_id="test-bundle", profile="bundle", root=config.ROOT))
    assert summary["records"] == 50
    assert summary["hash_mismatches"] == []
    assert summary["raw_missing"] == []
    assert all(doc.raw_sha256 for doc in docs)


@pytest.mark.skipif(bundle_missing, reason="gói 50 mẫu chưa được tải (data/mvp-candidates-50-2026-10-02)")
def test_bundle_quality_gate_keeps_most_documents() -> None:
    from scripts.elt.quality import apply_gates
    from scripts.elt.run_elt import parse_bundle

    from scripts.elt import config
    from scripts.elt.manifest import RunManifest

    docs, _ = parse_bundle(RunManifest(run_id="test-bundle", profile="bundle", root=config.ROOT))
    keep, quarantine, rejected = apply_gates(docs)
    assert len(keep) == 48
    assert len(quarantine) == 2
    assert rejected == []
