"""RV-07 — quyết định duyệt phải là nguyên tử.

Lỗi cũ: ``src/services/review.py`` ghi quyết định vào kho **trước** khi kiểm tra và áp dụng. Hệ quả:

* một quyết định sai (sai phiên bản, sai cổng) vẫn nằm lại trong ``review_decisions``;
* ``store.py`` đọc–sửa–ghi không có so-sánh-rồi-ghi, nên hai người duyệt cùng lúc thì người sau
  ghi đè người trước mà không ai biết.

Nay mọi thay đổi nằm trong **một** giao dịch, và giao dịch tự kiểm lại ``expected_version`` ngay
trước khi ghi.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app
from src.models.schemas import CheckpointKind, ClaimInput, RunStatus

CLAIM = {
    "claim_text": "aspirin gây chảy máu tiêu hoá",
    "drug": "aspirin",
    "event": "chảy máu tiêu hoá",
}

REASON = "Bài kiểm thử nguyên tử: lý do đủ dài để qua ngưỡng RV-04."
REVIEWER = "usr_nguoi_duyet"


def _headers(user_id: str, role: str = "reviewer") -> dict[str, str]:
    return {"X-Test-User": f"{user_id}:{role}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def atomic_client(monkeypatch, tmp_path):
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "atomic.db"))
    async with _client() as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


def _seed_case(created_by: str = "usr_tao_ca") -> tuple[str, int]:
    store = get_mvp_store()
    state, _ = store.create_investigation(ClaimInput(**CLAIM), created_by=created_by)
    state = store.save_state(
        state.model_copy(
            update={"run_status": RunStatus.WAITING_FOR_REVIEW, "checkpoint": CheckpointKind.ASSESSMENT}
        )
    )
    return state.investigation_id, state.version


def _decision(case_id: str, *, decision_id: str, expected_version: int, action: str = "reject") -> dict:
    return {
        "decision_id": decision_id,
        "action": action,
        "checkpoint": "assessment",
        "expected_version": expected_version,
        "reason": REASON,
    }


async def _decide(client: AsyncClient, case_id: str, payload: dict, *, user_id: str = REVIEWER):
    return await client.post(
        f"/api/v1/investigations/{case_id}/reviews", headers=_headers(user_id), json=payload
    )


@pytest.mark.asyncio
async def test_a_rejected_decision_leaves_no_trace(atomic_client: AsyncClient):
    """Quyết định sai phiên bản ⇒ 409 và **không** có dòng nào trong ``review_decisions``."""
    case_id, version = _seed_case()
    response = await _decide(
        atomic_client, case_id, _decision(case_id, decision_id="qđ-sai", expected_version=version + 5)
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "version_conflict"

    store = get_mvp_store()
    assert store.get_review_decision("qđ-sai") is None
    assert store.list_review_decisions(case_id) == []
    assert store.get_state(case_id).version == version
    assert [item for item in store.list_audit(case_id) if item["action"].startswith("review_")] == []


@pytest.mark.asyncio
async def test_a_wrong_checkpoint_decision_leaves_no_trace(atomic_client: AsyncClient):
    """Sai cổng duyệt ⇒ 409 và cũng không ghi gì."""
    case_id, version = _seed_case()
    payload = _decision(case_id, decision_id="qđ-sai-cong", expected_version=version)
    payload["checkpoint"] = "dossier"
    response = await _decide(atomic_client, case_id, payload)
    assert response.status_code == 409, response.text

    store = get_mvp_store()
    assert store.get_review_decision("qđ-sai-cong") is None
    assert store.list_review_decisions(case_id) == []


@pytest.mark.asyncio
async def test_self_review_is_refused_and_leaves_no_trace(atomic_client: AsyncClient):
    """Tách biệt nhiệm vụ (B1.5): người tạo ca tự duyệt ⇒ 403 và không ghi gì."""
    case_id, version = _seed_case(created_by=REVIEWER)
    response = await _decide(
        atomic_client, case_id, _decision(case_id, decision_id="qđ-tu-duyet", expected_version=version)
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["details"]["code"].lower() == "self_review_forbidden"

    store = get_mvp_store()
    assert store.get_review_decision("qđ-tu-duyet") is None
    assert store.get_state(case_id).version == version


@pytest.mark.asyncio
async def test_a_good_decision_is_recorded_with_its_resulting_version(atomic_client: AsyncClient):
    """Quyết định hợp lệ ghi kèm ``result_version``/``result_status`` để đối chiếu về sau."""
    case_id, version = _seed_case()
    response = await _decide(
        atomic_client, case_id, _decision(case_id, decision_id="qđ-dung", expected_version=version)
    )
    assert response.status_code == 200, response.text

    store = get_mvp_store()
    decision = store.get_review_decision("qđ-dung")
    assert decision is not None
    assert decision.reviewer_id == REVIEWER
    assert store.get_state(case_id).version == version + 1

    log = store.list_audit(case_id)
    recorded = [item for item in log if item["action"] == "review_reject"]
    assert len(recorded) == 1
    assert recorded[0]["payload"]["decision_id"] == "qđ-dung"
    assert recorded[0]["payload"]["result_version"] == version + 1


@pytest.mark.asyncio
async def test_two_interleaved_decisions_leave_exactly_one_winner(atomic_client: AsyncClient):
    """Hai người duyệt cùng phiên bản: đúng một người thắng, người kia nhận 409."""
    case_id, version = _seed_case()
    first, second = await asyncio.gather(
        _decide(
            atomic_client,
            case_id,
            _decision(case_id, decision_id="qđ-a", expected_version=version),
            user_id="usr_duyet_a",
        ),
        _decide(
            atomic_client,
            case_id,
            _decision(case_id, decision_id="qđ-b", expected_version=version),
            user_id="usr_duyet_b",
        ),
    )
    statuses = sorted([first.status_code, second.status_code])
    assert statuses == [200, 409], (first.text, second.text)

    store = get_mvp_store()
    stored = store.list_review_decisions(case_id)
    assert len(stored) == 1, "Chỉ quyết định thắng được ghi lại"
    assert store.get_state(case_id).version == version + 1


@pytest.mark.asyncio
async def test_replaying_the_same_decision_id_is_refused(atomic_client: AsyncClient):
    """Cùng ``decision_id`` gửi lại ⇒ 409 và không áp dụng lần thứ hai.

    Giữ nguyên hành vi có từ trước bản sửa này (``apply_review`` đã chặn như vậy ở ``31cbda0``):
    ``decision_id`` là duy nhất, gửi lại là xung đột chứ không phải "trả kết quả cũ".
    """
    case_id, version = _seed_case()
    payload = _decision(case_id, decision_id="qđ-lap", expected_version=version)
    first = await _decide(atomic_client, case_id, payload)
    assert first.status_code == 200, first.text
    after_first = get_mvp_store().get_state(case_id).version

    second = await _decide(atomic_client, case_id, payload)
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "idempotency_conflict"
    assert get_mvp_store().get_state(case_id).version == after_first
    assert len(get_mvp_store().list_review_decisions(case_id)) == 1
