"""Đối chiếu tài liệu thật của ``/api/v2`` với ``docs/spec/hospital-v2/schemas.json``.

``docs/contracts-hospital-v2.md`` giao cho tầng này việc bảo đảm tài liệu trả ra đúng lược đồ.
Bài kiểm ở ``test_v2_api.py`` khẳng định **từng trường** theo cách viết tay, nên nó chỉ bắt được
những gì người viết đã nghĩ tới. Bài này chạy thẳng bộ kiểm JSON Schema của hợp đồng trên tài liệu
**trả về qua HTTP** — bắt được cả những chỗ mô hình Pydantic cho qua mà lược đồ chặn, ví dụ một
trường tuỳ chọn bị ghi bằng ``null`` thay vì bỏ hẳn.

Lược đồ là bản đóng băng trong kho, không phải bản sao chép ở đây, nên hợp đồng đổi thì bài này đổi
theo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jsonschema import Draft202012Validator

from src.api.v2_routes import get_casework_store
from src.main import app
from src.services.casework.store import CaseWorkStore
from src.services.warehouse.db import get_warehouse_engine

SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "spec" / "hospital-v2" / "schemas.json"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    """Bộ kiểm cho một định nghĩa trong ``$defs``, kèm toàn bộ ``$defs`` để tham chiếu chéo chạy được."""
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": SPEC["$defs"]})


def _assert_matches(name: str, document: Any) -> None:
    errors = sorted(_validator(name).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        rendered = "\n".join(
            f"  - {'/'.join(str(part) for part in error.path) or '<gốc>'}: {error.message}" for error in errors
        )
        raise AssertionError(
            f"Tài liệu không khớp $defs/{name}:\n{rendered}\n\nTài liệu: {json.dumps(document, ensure_ascii=False)}"
        )


def _headers(role: str, user_id: str | None = None) -> dict[str, str]:
    return {"X-Test-User": f"{user_id or f'usr_{role}'}:{role}"}


@pytest_asyncio.fixture
async def client(tmp_path):
    engine = get_warehouse_engine(f"sqlite:///{tmp_path / 'contract.db'}")
    store = CaseWorkStore(engine)
    app.dependency_overrides[get_casework_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://contract") as http:
        yield http
    app.dependency_overrides.pop(get_casework_store, None)


def test_the_contract_file_is_the_frozen_one() -> None:
    """Nếu hợp đồng bị thay bằng bản khác thì các bài dưới đây đang kiểm nhầm thứ."""
    assert SPEC["$id"] == "https://vigilens.local/contracts/hospital-v2/schemas.json"
    assert {"WorkItem", "ScopeField", "CoverageReport", "Actor"} <= set(SPEC["$defs"])
    # ``scope`` không có định nghĩa riêng: nó nằm trong ``WorkItem`` với tám trường, hai trường bắt buộc.
    scope = SPEC["$defs"]["WorkItem"]["properties"]["scope"]
    assert scope["required"] == ["drug", "event"]
    assert set(scope["properties"]) == {
        "drug",
        "event",
        "population",
        "route",
        "dose",
        "time_window",
        "indication",
        "comparator",
    }


@pytest.mark.asyncio
async def test_every_document_the_router_returns_matches_the_contract(client):
    """Đi hết chín điểm cuối và soi từng tài liệu trả về bằng chính lược đồ của hợp đồng."""
    investigator = _headers("investigator", "usr_contract")
    reviewer = _headers("reviewer", "usr_contract_rev")

    created = await client.post(
        "/api/v2/work-items",
        json={
            "question": "Metformin có gây nhiễm toan lactic ở người suy thận giai đoạn 3b không?",
            "context": {
                "requester": {"id": "usr_contract"},
                "channel": "web",
                "raw_text": "Câu hỏi nguyên văn của bác sĩ.",
                "language": "vi",
            },
            "scope": {
                "drug": {"value": "metformin", "resolution": "confirmed", "source": "requester"},
                "event": {"resolution": "unknown"},
                "population": {"value": "người suy thận giai đoạn 3b", "resolution": "candidate"},
                "comparator": {"resolution": "unknown"},
            },
            "unknowns": [{"field": "dose", "reason": "Bác sĩ chưa nêu liều."}],
        },
        headers=investigator,
    )
    assert created.status_code == 201, created.text
    work_item = created.json()
    _assert_matches("WorkItem", work_item)

    bundle = await client.get(f"/api/v2/work-items/{work_item['work_item_id']}", headers=investigator)
    assert bundle.status_code == 200, bundle.text
    _assert_matches("WorkItem", bundle.json()["work_item"])

    listed = await client.get("/api/v2/work-items", headers=investigator)
    assert listed.status_code == 200, listed.text
    _assert_matches("WorkItemList", listed.json())

    link = await client.post(
        f"/api/v2/work-items/{work_item['work_item_id']}/investigations",
        json={"investigation_id": "INV-contract", "purpose": "initial"},
        headers=investigator,
    )
    assert link.status_code == 201, link.text
    _assert_matches("InvestigationLink", link.json())

    response = await client.post(
        f"/api/v2/work-items/{work_item['work_item_id']}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Chưa đủ bằng chứng.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 2,
                "sources_ok": ["pubmed"],
                "sources_empty": ["dailymed"],
                "sources_error": [],
                "abstract_only": True,
            },
        },
        headers=investigator,
    )
    assert response.status_code == 201, response.text
    professional_response = response.json()
    _assert_matches("ProfessionalResponse", professional_response)

    reviewed = await client.post(
        f"/api/v2/responses/{professional_response['response_id']}/review",
        json={"action": "approve", "reason": "Khớp phạm vi.", "expected_version": professional_response["version"]},
        headers=reviewer,
    )
    assert reviewed.status_code == 200, reviewed.text
    _assert_matches("ProfessionalResponse", reviewed.json())
    _assert_matches("ReviewRef", reviewed.json()["review"])

    follow_up = await client.post(
        f"/api/v2/work-items/{work_item['work_item_id']}/follow-ups",
        json={"kind": "recheck_source", "note": "Chạy lại khi có bản mới."},
        headers=investigator,
    )
    assert follow_up.status_code == 201, follow_up.text
    _assert_matches("FollowUp", follow_up.json())


@pytest.mark.asyncio
async def test_an_optional_field_is_absent_rather_than_null(client):
    """Hợp đồng cho phép trường tuỳ chọn **vắng mặt**, nhưng ``null`` thì bị ``additionalProperties`` chặn.

    Đây là lỗi mà bài kiểm viết tay bỏ sót: mô hình Pydantic ghi ``null`` cho mọi trường không đặt,
    và lược đồ từ chối đúng những giá trị đó.
    """
    created = await client.post(
        "/api/v2/work-items",
        json={
            "question": "Câu hỏi tối thiểu?",
            "context": {
                "requester": {"id": "usr_contract"},
                "channel": "api",
                "raw_text": "Câu hỏi tối thiểu.",
                "language": "vi",
            },
        },
        headers=_headers("investigator", "usr_contract"),
    )
    assert created.status_code == 201, created.text
    work_item = created.json()
    _assert_matches("WorkItem", work_item)

    assert set(work_item["context"]["requester"]) == {"id"}
    assert "source_system" not in work_item["context"]
    for name in ("drug", "event"):
        assert set(work_item["scope"][name]) == {"value", "resolution"}, work_item["scope"][name]
