

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
    store.save_evidence(
        state.investigation_id,
        _evidence("EVI-CU"),
    )
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
        assert reopened.get_evidence(state.investigation_id)[0].evidence_id == "EVI-CU"
    finally:
        reopened.close()


def test_migration_leaves_a_confidence_field_of_another_meaning_alone(tmp_path):
    """Chỉ xoá ``confidence`` của bằng chứng/kết luận, không xoá trường cùng tên khác nghĩa."""
    from src.services.store import _strip_confidence

    payload = {"payload": {"confidence": 0.9}, "evidence": [{"evidence_id": "EVI-1", "confidence": 0.1}]}
    assert _strip_confidence(payload) is True
    assert payload["payload"]["confidence"] == 0.9
    assert "confidence" not in payload["evidence"][0]
