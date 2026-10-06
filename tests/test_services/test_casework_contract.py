"""Bộ kiểm hợp đồng dùng chung cho cả cửa ghi và cửa đọc — khoá lại chính nó.

Vì sao có tệp này: `src/services/casework/contract.py` ra đời để **một luật chạy ở cả hai đầu**, mà
trước tệp này thì nó **không có bài kiểm nào**. Hệ quả đã đo được: bộ kiểm mặc định của ``jsonschema``
coi ``1.0`` là số nguyên và coi ``format`` là chú thích, nên cùng một tài liệu bị API trả 422 mà cửa
ghi vẫn nhận và ghi vào kho. Bài ở đây khoá cả hai lỗ đó, và khoá cả tính cô lập của bộ kiểm định dạng.
"""

from __future__ import annotations

import copy
import json

from src.services.casework.contract import (
    _SCHEMAS_PATH,
    contract_schemas,
    contract_violations,
)

VALID_BUNDLE = {
    "bundle_id": "eb_1",
    "work_item_id": "wi_1",
    "investigation_id": "INV-1",
    "created_at": "2026-01-01T00:00:00Z",
    "items": [],
    "gaps": [],
    "coverage": {
        "documents_retrieved": 0,
        "sources_ok": [],
        "sources_empty": [],
        "sources_error": [],
        "abstract_only": False,
    },
    "assessment_status": "insufficient_evidence",
    "source_errors": [],
}


def _bundle(**changes):
    document = copy.deepcopy(VALID_BUNDLE)
    document.update(changes)
    return document


def test_a_valid_bundle_has_no_violations():
    assert contract_violations("EvidenceBundle", VALID_BUNDLE) == []


def test_a_missing_required_field_is_reported_with_its_path():
    document = _bundle()
    del document["investigation_id"]
    # ``jsonschema`` báo trường thiếu ở cấp đối tượng, còn tên trường nằm trong thông điệp.
    assert contract_violations("EvidenceBundle", document) == [
        "<gốc>: 'investigation_id' is a required property"
    ]


def test_an_unknown_extra_property_is_rejected():
    """``additionalProperties: false`` là thứ giữ cho tài liệu không phình ra ngoài hợp đồng."""
    violations = contract_violations("EvidenceBundle", _bundle(trường_lạ="x"))
    assert violations == [
        "<gốc>: Additional properties are not allowed ('trường_lạ' was unexpected)"
    ]


def test_a_nested_violation_names_the_full_path():
    document = _bundle(items=[{"evidence_id": "EVI-1"}])
    violations = contract_violations("EvidenceBundle", document)
    assert any(v.startswith("items/0: ") for v in violations), violations


# ------------------------------------------------------------------ hai lỗ đã đo được
def test_a_float_is_not_an_integer_even_though_json_schema_says_so():
    """JSON Schema 2020-12 coi ``1.0`` là số nguyên; Pydantic ``strict=True`` thì không.

    Đây là khe hở đã đo được: cùng một tài liệu bị API trả 422 mà cửa ghi vẫn nhận và ghi ``1.0``
    vào ``coverage_json``. Cửa ghi phải chặt bằng API, nếu không thì "một luật" chỉ đúng trên giấy.
    """
    document = _bundle(coverage={**VALID_BUNDLE["coverage"], "documents_retrieved": 1.0})
    assert contract_violations("EvidenceBundle", document) == [
        "coverage/documents_retrieved: 1.0 is not of type 'integer'"
    ]


def test_a_boolean_is_not_an_integer():
    """``bool`` là lớp con của ``int`` trong Python, nên phải loại riêng."""
    document = _bundle(coverage={**VALID_BUNDLE["coverage"], "documents_retrieved": True})
    assert contract_violations("EvidenceBundle", document) == [
        "coverage/documents_retrieved: True is not of type 'integer'"
    ]


def test_a_real_integer_still_passes():
    document = _bundle(coverage={**VALID_BUNDLE["coverage"], "documents_retrieved": 3})
    assert contract_violations("EvidenceBundle", document) == []


def test_a_timestamp_must_be_rfc3339_with_a_timezone():
    """``Timestamp`` mô tả "RFC 3339, luôn có múi giờ" — đó là ràng buộc, không phải trang trí.

    Vì sao phải tự kiểm: ``jsonschema`` để ``format`` thành chú thích trừ khi có gói kiểm định dạng,
    mà gói đó không nằm trong phụ thuộc. Không có bài này thì ``created_at: "khong-phai-ngay"`` lọt.
    """
    for bad_value in ("khong-phai-ngay", "2026-01-01", "2026-01-01T00:00:00"):
        violations = contract_violations("EvidenceBundle", _bundle(created_at=bad_value))
        assert violations == [f"created_at: {bad_value!r} is not a 'date-time'"], bad_value


def test_a_timestamp_with_an_offset_is_accepted():
    for good_value in ("2026-01-01T00:00:00Z", "2026-01-01T00:00:00+07:00", "2026-01-01t00:00:00z"):
        assert contract_violations("EvidenceBundle", _bundle(created_at=good_value)) == [], good_value


def test_the_timestamp_the_store_actually_writes_is_accepted():
    """Định dạng thật trong kho là ``2026-10-06T04:35:48.602071+00:00``; luật chặt hơn không được đánh đổ nó."""
    assert contract_violations(
        "EvidenceBundle", _bundle(created_at="2026-10-06T04:35:48.602071+00:00")
    ) == []


# ------------------------------------------------------------------ tính cô lập và tính ổn định
def test_the_shared_format_checker_is_not_modified():
    """Đăng ký ``date-time`` phải nằm trong thực thể riêng, không sửa luật dùng chung của tiến trình."""
    from jsonschema import FormatChecker

    assert "date-time" not in FormatChecker.checkers


def test_violations_are_sorted_by_path_so_output_is_deterministic():
    document = _bundle(created_at="hong", coverage={"documents_retrieved": 1.0})
    violations = contract_violations("EvidenceBundle", document)
    assert violations == sorted(violations, key=lambda item: item.split(": ", 1)[0])
    assert len(violations) >= 2


def test_the_validator_reads_the_frozen_schema_file_not_a_copy():
    """Lược đồ là hợp đồng đóng băng: bộ kiểm phải đọc chính tệp đó, không chép lại luật."""
    on_disk = json.loads(_SCHEMAS_PATH.read_text(encoding="utf-8"))
    assert contract_schemas() == on_disk
    assert "EvidenceBundle" in contract_schemas()["$defs"]


def test_every_document_definition_can_be_checked():
    """Mọi ``$defs`` phải dựng được bộ kiểm — một tham chiếu chéo hỏng sẽ lộ ra ở đây."""
    for name in contract_schemas()["$defs"]:
        assert isinstance(contract_violations(name, {}), list), name
