"""EV-07 + API-03: bỏ điểm tin cậy giả, thay bằng báo phủ đếm từ bằng chứng thật.

``confidence`` cũ là hằng số viết tay (0.0/0.2/0.3/0.4/0.5/0.9) chưa từng hiệu chỉnh bằng dữ liệu
thật. Nó nằm ngay cạnh trích đoạn nên bị đọc như xác suất đúng — trong khi thực chất chỉ phản ánh
nhánh ``if`` nào đã chạy. Bộ kiểm thử này khoá hai điều:

* không còn trường ``confidence`` nào trong hợp đồng bằng chứng/kết luận, và không nhánh nào sinh ra
  con số đó nữa;
* ``coverage`` đếm từ bằng chứng **đang hoạt động**, nên nó đổi khi bằng chứng đổi, và nói đúng
  trường nào của câu hỏi chưa có bằng chứng nào chạm tới.
"""

from __future__ import annotations

import pytest

from src.models.schemas import (
    AssessmentResult,
    AssessmentStatus,
    EvidenceScope,
    EvidenceUnit,
    NormalizedClaim,
    Stance,
)
from src.services.assessment import COVERAGE_FIELDS, assess_evidence


def _evidence(
    evidence_id: str = "EVI-1",
    *,
    stance: Stance = Stance.SUPPORTS,
    source: str = "pubmed",
    scope: EvidenceScope | None = None,
    excluded: bool = False,
) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=evidence_id,
        doc_id=f"DOC-{evidence_id}",
        source=source,  # type: ignore[arg-type]
        stance=stance,
        quote="Metformin was associated with lactic acidosis in adults.",
        locator={"start": 0, "end": 20},
        scope=scope or EvidenceScope(),
        excluded=excluded,
    )


def _claim(**overrides) -> NormalizedClaim:
    values = {
        "claim_text": "metformin gây lactic acidosis.",
        "drug_ingredient": "metformin",
        "event_term": "lactic acidosis",
    }
    values.update(overrides)
    return NormalizedClaim(**values)


# ---------------------------------------------------------------------------- EV-07


def test_evidence_unit_has_no_confidence_field():
    assert "confidence" not in EvidenceUnit.model_fields


def test_assessment_result_has_no_confidence_field():
    assert "confidence" not in AssessmentResult.model_fields


def test_old_confidence_payload_is_rejected_not_silently_ignored():
    """Hợp đồng dùng ``extra="forbid"``: dữ liệu cũ mang ``confidence`` phải lỗi to, không im lặng."""
    with pytest.raises(ValueError):
        EvidenceUnit(
            evidence_id="EVI-1",
            doc_id="DOC-1",
            source="pubmed",
            stance=Stance.SUPPORTS,
            quote="metformin",
            locator={"start": 0, "end": 8},
            confidence=0.5,
        )


def test_no_assessment_branch_emits_a_number_that_looks_like_a_probability():
    """Mọi nhánh kết luận đều phải chạy mà không sinh ra ``confidence``."""
    claim = _claim()
    cases = [
        [],
        [_evidence("EVI-FAERS", source="faers")],
        [_evidence("EVI-1"), _evidence("EVI-2", stance=Stance.CONTRADICTS)],
        [_evidence("EVI-1", scope=EvidenceScope(population="người lớn"))],
    ]
    for evidence in cases:
        result = assess_evidence(evidence, claim)
        assert "confidence" not in result.model_dump()
        assert result.assessment_status in set(AssessmentStatus)


# ---------------------------------------------------------------------------- API-03


def test_coverage_covers_exactly_the_fields_the_ui_reads():
    assert set(COVERAGE_FIELDS) == {"drug", "adverseEvent", "population", "dose", "route", "timeWindow"}


def test_claim_fields_absent_from_the_question_are_marked_missing():
    result = assess_evidence([_evidence()], _claim())
    assert result.coverage["population"] == "missing"
    assert result.coverage["dose"] == "missing"
    assert result.coverage["route"] == "missing"
    assert result.coverage["timeWindow"] == "missing"


def test_claim_field_with_no_evidence_at_all_is_not_specified():
    result = assess_evidence([_evidence()], _claim(population="người lớn"))
    assert result.coverage["population"] == "not_specified"


def test_claim_field_with_a_matching_evidence_value_is_verified():
    result = assess_evidence(
        [_evidence(scope=EvidenceScope(population="người lớn"))], _claim(population="người lớn")
    )
    assert result.coverage["population"] == "verified"


def test_claim_field_with_a_different_evidence_value_is_partial():
    result = assess_evidence(
        [_evidence(scope=EvidenceScope(population="trẻ em"))], _claim(population="người lớn")
    )
    assert result.coverage["population"] == "partial"


def test_drug_and_event_are_verified_when_any_evidence_exists():
    """Mọi bằng chứng đều được truy hồi theo đúng thuốc/biến cố của câu hỏi."""
    result = assess_evidence([_evidence()], _claim())
    assert result.coverage["drug"] == "verified"
    assert result.coverage["adverseEvent"] == "verified"


def test_coverage_counts_only_active_evidence():
    """Bằng chứng bị reviewer loại không được tính là đã phủ."""
    excluded = _evidence("EVI-X", scope=EvidenceScope(population="người lớn"), excluded=True)
    result = assess_evidence([excluded], _claim(population="người lớn"))
    assert result.coverage["population"] == "not_specified"


def test_coverage_changes_when_evidence_changes():
    """Điểm mấu chốt của API-03: báo phủ nói về *bằng chứng*, không phải về *câu hỏi*."""
    claim = _claim(population="người lớn")
    without = assess_evidence([_evidence()], claim)
    with_match = assess_evidence([_evidence(scope=EvidenceScope(population="người lớn"))], claim)
    assert without.coverage != with_match.coverage


def test_empty_evidence_marks_every_field_not_specified():
    result = assess_evidence([], _claim(population="người lớn"))
    assert result.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert set(result.coverage) == set(COVERAGE_FIELDS)
    assert set(result.coverage.values()) == {"not_specified"}


# ------------------------------------------------------------------- Di trú dữ liệu cũ (EV-07)


def test_legacy_rows_that_still_carry_confidence_still_load(tmp_path):
    """Hợp đồng ``extra="forbid"`` làm hàng cũ mang ``confidence`` không đọc được nữa.

    Nếu không di trú, mỗi cuộc điều tra ghi trước thay đổi này sẽ trả 500. Bài này dựng đúng tình
    huống đó: ghi một hàng có ``confidence``, rồi mở lại kho và đọc.
    """
    import json
    import sqlite3

    from src.models.schemas import ClaimInput
    from src.services.store import MvpStore

    path = tmp_path / "cu.sqlite3"
    store = MvpStore(path)
    state, _ = store.create_investigation(
        ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis")
    )
    store.save_evidence(state.investigation_id, _evidence("EVI-CU"))
    store.close()

    # Giả lập hàng ghi bằng mã cũ: nhét lại ``confidence`` vào JSON đã lưu.
    connection = sqlite3.connect(path)
    raw = json.loads(connection.execute("SELECT state_json FROM investigations").fetchone()[0])
    raw["assessment"] = {"assessment_status": "insufficient_evidence", "rationale": "cũ", "confidence": 0.4}
    connection.execute("UPDATE investigations SET state_json = ?", (json.dumps(raw),))
    payload = json.loads(connection.execute("SELECT payload_json FROM evidence_versions").fetchone()[0])
    payload["confidence"] = 0.0
    connection.execute("UPDATE evidence_versions SET payload_json = ?", (json.dumps(payload),))
    connection.commit()
    connection.close()

    reopened = MvpStore(path)  # ``_migrate`` chạy ở đây
    try:
        loaded = reopened.get_state(state.investigation_id)
        assert loaded.investigation_id == state.investigation_id
        assert loaded.assessment is not None
        assert "confidence" not in loaded.assessment.model_dump()
        assert reopened.list_evidence(state.investigation_id)[0].evidence_id == "EVI-CU"
    finally:
        reopened.close()


def test_migration_leaves_a_confidence_field_of_another_meaning_alone():
    """Chỉ xoá ``confidence`` của bằng chứng/kết luận, không xoá trường cùng tên khác nghĩa."""
    from src.services.store import _strip_confidence

    payload = {"payload": {"confidence": 0.9}, "evidence": [{"evidence_id": "EVI-1", "confidence": 0.1}]}
    assert _strip_confidence(payload) is True
    assert payload["payload"]["confidence"] == 0.9
    assert "confidence" not in payload["evidence"][0]
