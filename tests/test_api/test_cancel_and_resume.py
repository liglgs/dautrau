"""RT-04 và RV-06 — ca đã hủy không hồi sinh, và khoá chống lặp bền vững qua khởi động lại.

RT-04: ``/continue`` trước đây chặn ``checkpoint``, ``COMPLETED``, ``RUNNING`` nhưng **quên**
``CANCELLED``, nên một ca đã hủy vẫn chạy tiếp được và kết thúc ở trạng thái "hoàn tất".

RV-06: ``_resume_seen`` nằm trong RAM của tiến trình. Khởi động lại là mất, nên cú bấm trùng sau
khi khởi động lại vẫn tạo lượt chạy thứ hai. Nay khoá nằm trong bảng ``resume_requests``.
"""

from __future__ import annotations

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

OWNER = "usr_chu_ca"


def _headers(user_id: str = OWNER, role: str = "investigator") -> dict[str, str]:
    return {"X-Test-User": f"{user_id}:{role}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def resume_client(monkeypatch, tmp_path):
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "resume.db"))
    async with _client() as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


def _seed_case(*, run_status: RunStatus = RunStatus.WAITING_FOR_REVIEW) -> str:
    store = get_mvp_store()
    state, _ = store.create_investigation(ClaimInput(**CLAIM), created_by=OWNER)
    store.save_state(state.model_copy(update={"run_status": run_status, "checkpoint": None}))
    return state.investigation_id


@pytest.mark.asyncio
async def test_cancelled_case_cannot_be_resumed(resume_client: AsyncClient):
    """RT-04: hủy rồi chạy tiếp ⇒ 409 ``invalid_state``, và trạng thái vẫn là ``cancelled``."""
    store = get_mvp_store()
    case_id = _seed_case()
    cancel = await resume_client.post(f"/api/v1/investigations/{case_id}/cancel", headers=_headers())
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["run_status"] == "cancelled"

    version = store.get_state(case_id).version
    resumed = await resume_client.post(
        f"/api/v1/investigations/{case_id}/continue",
        headers={**_headers(), "Idempotency-Key": "chay-tiep-sau-khi-huy"},
        json={"expected_version": version},
    )
    assert resumed.status_code == 409, resumed.text
    body = resumed.json()
    assert body["error"]["code"] == "invalid_state"
    assert body["error"]["details"]["run_status"] == "cancelled"
    assert store.get_state(case_id).run_status is RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancelled_case_does_not_flip_to_completed(resume_client: AsyncClient):
    """RT-04: sau khi bị từ chối, trạng thái không được nhảy sang ``completed``."""
    store = get_mvp_store()
    case_id = _seed_case()
    await resume_client.post(f"/api/v1/investigations/{case_id}/cancel", headers=_headers())
    for _ in range(3):
        await resume_client.post(
            f"/api/v1/investigations/{case_id}/continue",
            headers={**_headers(), "Idempotency-Key": "bam-lai-nhieu-lan"},
            json={"expected_version": store.get_state(case_id).version},
        )
    assert store.get_state(case_id).run_status is RunStatus.CANCELLED


@pytest.mark.asyncio
async def test_completed_case_cannot_be_resumed(resume_client: AsyncClient):
    """Hàng rào cũ vẫn còn: ca đã hoàn tất không chạy tiếp."""
    store = get_mvp_store()
    case_id = _seed_case(run_status=RunStatus.COMPLETED)
    response = await resume_client.post(
        f"/api/v1/investigations/{case_id}/continue",
        headers={**_headers(), "Idempotency-Key": "chay-tiep-ca-da-xong"},
        json={"expected_version": store.get_state(case_id).version},
    )
    assert response.status_code == 409
    assert response.json()["error"]["details"]["run_status"] == "completed"


@pytest.mark.asyncio
async def test_checkpoint_still_blocks_resume(resume_client: AsyncClient):
    """Ca còn cổng duyệt chưa xử lý vẫn bị chặn — thứ tự kiểm không đổi."""
    store = get_mvp_store()
    case_id = _seed_case()
    state = store.get_state(case_id)
    store.save_state(state.model_copy(update={"checkpoint": CheckpointKind.ASSESSMENT}))
    response = await resume_client.post(
        f"/api/v1/investigations/{case_id}/continue",
        headers={**_headers(), "Idempotency-Key": "chay-tiep-khi-con-cong"},
        json={"expected_version": store.get_state(case_id).version},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state"
    assert response.json()["error"]["details"]["checkpoint"] == "assessment"


@pytest.mark.asyncio
async def test_expected_version_is_mandatory(resume_client: AsyncClient):
    """RV-06: thiếu ``expected_version`` ⇒ 422, không phải chạy luôn."""
    case_id = _seed_case()
    response = await resume_client.post(
        f"/api/v1/investigations/{case_id}/continue", headers=_headers(), json={}
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_resume_lock_survives_a_restart(resume_client: AsyncClient, tmp_path):
    """RV-06: khoá chống lặp nằm trong cơ sở dữ liệu nên sống qua lần khởi động lại."""
    store = get_mvp_store()
    case_id = _seed_case()
    version = store.get_state(case_id).version
    payload = {"expected_version": version}
    headers = {**_headers(), "Idempotency-Key": "cung-mot-cu-bam"}

    first = await resume_client.post(
        f"/api/v1/investigations/{case_id}/continue", headers=headers, json=payload
    )
    assert first.status_code == 202, first.text
    assert first.json()["resumed"] is True

    # Mô phỏng khởi động lại tiến trình: dựng lại runner/store trên **cùng tệp** cơ sở dữ liệu.
    reset_mvp()
    configure_mvp(str(tmp_path / "resume.db"))

    second = await resume_client.post(
        f"/api/v1/investigations/{case_id}/continue", headers=headers, json=payload
    )
    assert second.status_code == 202, second.text
    assert second.json()["resumed"] is False, "Cú bấm trùng sau khởi động lại phải bị nhận ra"


@pytest.mark.asyncio
async def test_resume_lock_does_not_leak_between_cases(resume_client: AsyncClient):
    """Cùng một khoá chống lặp cho hai ca khác nhau: khoá chỉ có nghĩa trong từng ca."""
    store = get_mvp_store()
    first_case = _seed_case()
    second_case = _seed_case()
    headers = {**_headers(), "Idempotency-Key": "khoa-dung-chung"}

    first = await resume_client.post(
        f"/api/v1/investigations/{first_case}/continue",
        headers=headers,
        json={"expected_version": store.get_state(first_case).version},
    )
    assert first.status_code == 202, first.text

    second = await resume_client.post(
        f"/api/v1/investigations/{second_case}/continue",
        headers=headers,
        json={"expected_version": store.get_state(second_case).version},
    )
    # Ca thứ hai có thể bị 429 vì runner đang bận với ca thứ nhất — điều phải khẳng định là nó
    # **không** bị coi là cú bấm trùng của ca kia.
    assert second.status_code in (202, 429), second.text
    if second.status_code == 202:
        assert second.json()["resumed"] is True
