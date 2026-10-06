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
    """Trả cả kho: gói bằng chứng không có điểm cuối ghi, phải gieo thẳng qua kho."""
    engine = get_warehouse_engine(f"sqlite:///{tmp_path / 'contract.db'}")
    store = CaseWorkStore(engine)
    app.dependency_overrides[get_casework_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://contract") as http:
        yield http, store
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
    client, store = client
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
                "source_system": {"name": "his-bv-1", "record_id": "HS-9", "deidentified": True},
                "attachments": [{"kind": "file", "ref": "hoso.pdf", "sha256": "a" * 64}],
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
        json={
            "investigation_id": "INV-contract",
            "purpose": "initial",
            "run_summary": {"steps_used": 3, "documents_used": 2, "stop_reason": "du_budget"},
        },
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

    seeded = store.add_evidence_bundle(
        work_item["work_item_id"],
        investigation_id="INV-contract",
        items=[
            {
                "evidence_id": "EVI-contract",
                "doc_id": "PMID-1",
                "source": "pubmed",
                "evidence_type": "observational",
                "stance": "supports",
                "quote": "Trích đoạn nguyên văn từ tài liệu.",
                "locator": {"start": 0, "end": 31, "section": "Tóm tắt"},
                "retrieval": "abstract_only",
                "scope_match": "match",
                "quality_flags": ["abstract_only"],
            }
        ],
        gaps=[{"kind": "missing_evidence", "detail": "Chưa có nhóm chứng.", "next_action": "Tìm thêm."}],
        coverage={
            "documents_retrieved": 1,
            "sources_ok": ["pubmed"],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": True,
        },
        assessment_status="insufficient_evidence",
        source_errors=[],
        limitations=["Chỉ có tóm tắt."],
    )
    assert seeded["bundle_id"]

    bundle_response = await client.get(
        f"/api/v2/work-items/{work_item['work_item_id']}/evidence-bundle", headers=investigator
    )
    assert bundle_response.status_code == 200, bundle_response.text
    _assert_matches("EvidenceBundle", bundle_response.json())

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
    client, _ = client
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


@pytest.mark.asyncio
async def test_the_documents_inside_the_work_item_envelope_match_too(client):
    """Lớp bọc của ``GET /work-items/{id}`` chở bốn loại tài liệu con — mỗi loại phải khớp lược đồ.

    Bản trước của tệp này chỉ soi cấu trúc lớp bọc, nên một gói bằng chứng sai lược đồ vẫn đi ra
    nguyên vẹn trong ``evidence_bundles[]`` mà không bài nào bắt. Đó là lý do bài này tồn tại: tài
    liệu con là chỗ dễ lọt nhất vì chúng không đi qua một mô hình Pydantic nào.
    """
    client, store = client
    investigator = _headers("investigator", "usr_envelope")

    created = await client.post(
        "/api/v2/work-items",
        json={
            "question": "Metformin có gây nhiễm toan lactic không?",
            "context": {
                "requester": {"id": "usr_envelope"},
                "channel": "web",
                "raw_text": "Câu hỏi nguyên văn.",
                "language": "vi",
            },
        },
        headers=investigator,
    )
    assert created.status_code == 201, created.text
    work_item_id = created.json()["work_item_id"]

    link = await client.post(
        f"/api/v2/work-items/{work_item_id}/investigations",
        json={"investigation_id": "INV-envelope", "purpose": "initial", "state": "running"},
        headers=investigator,
    )
    assert link.status_code == 201, link.text

    response = await client.post(
        f"/api/v2/work-items/{work_item_id}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 0,
                "sources_ok": [],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": False,
            },
        },
        headers=investigator,
    )
    assert response.status_code == 201, response.text

    follow_up = await client.post(
        f"/api/v2/work-items/{work_item_id}/follow-ups",
        json={"kind": "recheck_source", "note": "Chạy lại khi có bản mới."},
        headers=investigator,
    )
    assert follow_up.status_code == 201, follow_up.text

    store.add_evidence_bundle(
        work_item_id,
        investigation_id="INV-envelope",
        items=[
            {
                "evidence_id": "EVI-envelope",
                "doc_id": "PMID-2",
                "source": "pubmed",
                "stance": "uncertain",
                "quote": "Trích đoạn.",
                "locator": {"start": 0, "end": 10},
                "retrieval": "abstract_only",
            }
        ],
        gaps=[],
        coverage={
            "documents_retrieved": 1,
            "sources_ok": ["pubmed"],
            "sources_empty": [],
            "sources_error": [],
            "abstract_only": True,
        },
        assessment_status="insufficient_evidence",
    )

    envelope = await client.get(f"/api/v2/work-items/{work_item_id}", headers=investigator)
    assert envelope.status_code == 200, envelope.text
    document = envelope.json()

    _assert_matches("WorkItem", document["work_item"])
    for name, child, schema in (
        ("investigation_links", document["investigation_links"], "InvestigationLink"),
        ("evidence_bundles", document["evidence_bundles"], "EvidenceBundle"),
        ("responses", document["responses"], "ProfessionalResponse"),
        ("follow_ups", document["follow_ups"], "FollowUp"),
    ):
        assert child, f"{name} phải có ít nhất một phần tử để phép kiểm có nghĩa"
        for index, item in enumerate(child):
            try:
                _assert_matches(schema, item)
            except AssertionError as error:
                raise AssertionError(f"{name}[{index}] sai lược đồ:\n{error}") from error


@pytest.mark.asyncio
async def test_a_review_inside_the_envelope_matches_too(client):
    """Phiếu trả lời trong lớp bọc chở thêm ``review`` — chính là dấu duyệt, phải khớp ``ReviewRef``."""
    client, _ = client
    investigator = _headers("investigator", "usr_envelope_rev2")
    reviewer = _headers("reviewer", "usr_envelope_rev3")

    created = await client.post(
        "/api/v2/work-items",
        json={
            "question": "Câu hỏi để duyệt?",
            "context": {
                "requester": {"id": "usr_envelope_rev2"},
                "channel": "web",
                "raw_text": "Câu hỏi.",
                "language": "vi",
            },
        },
        headers=investigator,
    )
    work_item_id = created.json()["work_item_id"]
    response = await client.post(
        f"/api/v2/work-items/{work_item_id}/responses",
        json={
            "sections": [{"key": "summary", "title": "Tóm tắt", "text": "Nháp.", "citations": []}],
            "assessment_status": "insufficient_evidence",
            "coverage": {
                "documents_retrieved": 0,
                "sources_ok": [],
                "sources_empty": [],
                "sources_error": [],
                "abstract_only": False,
            },
        },
        headers=investigator,
    )
    assert response.status_code == 201, response.text
    document = response.json()

    reviewed = await client.post(
        f"/api/v2/responses/{document['response_id']}/review",
        json={"action": "approve", "reason": "Khớp phạm vi.", "expected_version": document["version"]},
        headers=reviewer,
    )
    assert reviewed.status_code == 200, reviewed.text

    envelope = await client.get(f"/api/v2/work-items/{work_item_id}", headers=investigator)
    assert envelope.status_code == 200, envelope.text
    stored = envelope.json()["responses"][0]
    _assert_matches("ProfessionalResponse", stored)
    assert stored["review"] is not None, "quyết định duyệt phải nằm trong lớp bọc"
    _assert_matches("ReviewRef", stored["review"])


@pytest.mark.asyncio
async def test_every_error_the_v2_router_returns_matches_the_contract(client):
    """**Mọi** phản hồi lỗi của ``/api/v2`` phải khớp ``$defs/ApiError``, không chỉ các ca đẹp.

    Trước đây bài này không tồn tại, nên envelope dùng chung thêm khoá ``retryable`` và lặp khoá
    phẳng ở cấp gốc mà không ai thấy: hợp đồng khai ``additionalProperties: false`` nên **mọi**
    phản hồi 4xx/5xx của tầng mới đều trượt kiểm, kể cả 409/422 mà hợp đồng khai báo tường minh.
    Một bộ kiểm chỉ chạy trên đường thành công thì không phải bộ kiểm.
    """
    http, store = client
    created = await http.post(
        "/api/v2/work-items",
        json={
            "question": "Metformin có gây nhiễm toan lactic ở người suy thận giai đoạn 3b không?",
            "context": {
                "requester": {"id": "usr_investigator"},
                "channel": "api",
                "raw_text": "Metformin có gây nhiễm toan lactic ở người suy thận giai đoạn 3b không?",
                "language": "vi",
            },
        },
        headers=_headers("investigator"),
    )
    assert created.status_code == 201, created.text
    work_item_id = created.json()["work_item_id"]

    cases: list[tuple[str, Any, dict[str, str], int]] = [
        # (tên ca, thân yêu cầu, header, mã HTTP mong đợi)
        ("404 ca không tồn tại", None, _headers("investigator"), 404),
        # 403 thật phải là ca nhìn thấy được nhưng không đủ quyền: người điều tra tự đổi chủ sở hữu
        # ca của chính mình. Ca ngoài phạm vi trả 404 chứ không trả 403 — đó là chủ ý, không phải ca này.
        ("403 thiếu quyền queue:assign", {"expected_version": 1, "owner": {"id": "usr_khac"}}, _headers("investigator"), 403),
        ("422 thiếu expected_version", {"question": "Câu hỏi khác?"}, _headers("investigator"), 422),
        ("409 phiên bản cũ", {"expected_version": 99, "priority": "urgent"}, _headers("investigator"), 409),
        ("401 thiếu danh tính", None, {}, 401),
    ]
    checked = 0
    for name, body, headers, expected_status in cases:
        if body is None:
            response = await http.get("/api/v2/work-items/wi_khong_ton_tai", headers=headers)
        else:
            response = await http.patch(f"/api/v2/work-items/{work_item_id}", json=body, headers=headers)
        assert response.status_code == expected_status, f"{name}: {response.status_code} {response.text}"
        _assert_matches("ApiError", response.json())
        # Envelope hợp đồng không được lặp khoá ở cấp gốc — đó là thứ chỉ khách VMEC cũ cần.
        assert set(response.json()) == {"error"}, name
        checked += 1

    # Lỗi không đi qua ``MvpError`` cũng phải đúng: 405 do sai phương thức, và 404 của định tuyến.
    method_not_allowed = await http.put(f"/api/v2/work-items/{work_item_id}", headers=_headers("investigator"))
    assert method_not_allowed.status_code == 405, method_not_allowed.text
    _assert_matches("ApiError", method_not_allowed.json())
    checked += 1

    assert checked == 6


@pytest.mark.asyncio
async def test_a_client_cannot_smuggle_a_bad_request_id_into_the_contract(client):
    """``request_id`` nằm trong envelope lỗi, nên mã khách gửi vào không được làm hỏng hợp đồng.

    ``$defs/Identifier`` chỉ nhận ``^[A-Za-z0-9][A-Za-z0-9._:-]*$`` và tối đa 120 ký tự. Trước đây
    middleware cắt ``X-Request-Id`` còn 128 ký tự rồi dùng nguyên, nên một mã dài hay chứa ký tự
    lạ khiến chính phản hồi lỗi của tầng mới trượt kiểm hợp đồng — khách tự phá hợp đồng của mình.
    """
    http, _ = client
    for bad in ("!!!khong-hop-le!!!", "x" * 200, "  "):
        response = await http.get(
            "/api/v2/work-items/wi_khong_ton_tai",
            headers={**_headers("investigator"), "X-Request-Id": bad},
        )
        assert response.status_code == 404, response.text
        _assert_matches("ApiError", response.json())
        returned = response.json()["error"]["request_id"]
        assert returned != bad.strip(), "mã không hợp lệ phải bị thay bằng mã tự sinh"

    # Mã hợp lệ thì phải giữ nguyên, nếu không thì tra vết xuyên tầng mất tác dụng.
    response = await http.get(
        "/api/v2/work-items/wi_khong_ton_tai",
        headers={**_headers("investigator"), "X-Request-Id": "bridge-01.abc:xyz"},
    )
    assert response.json()["error"]["request_id"] == "bridge-01.abc:xyz"
    assert response.headers["X-Request-Id"] == "bridge-01.abc:xyz"


@pytest.mark.asyncio
async def test_the_old_api_keeps_its_wide_envelope(client):
    """``/api/v1`` phải giữ nguyên envelope cũ: khách VMEC đọc trực tiếp khoá phẳng ở cấp gốc.

    Bài này khoá lại rằng việc tách envelope cho tầng mới không lặng lẽ bỏ khoá phẳng của tầng cũ.
    """
    http, _ = client
    response = await http.get("/api/v1/khong-ton-tai", headers=_headers("investigator"))
    body = response.json()
    assert response.status_code in (401, 403, 404), response.text
    assert "error" in body
    assert "retryable" in body["error"], "tầng cũ vẫn phải giữ khoá retryable"
    assert "code" in body and "message" in body, "tầng cũ vẫn phải giữ khoá phẳng ở cấp gốc"


@pytest.mark.asyncio
async def test_unknown_is_null_and_never_an_empty_string(client):
    """Chốt IN-06: "chưa rõ" là `value: null` + `resolution: "unknown"`, không phải chuỗi sentinel.

    Phân biệt được hai trạng thái khác nhau về nghĩa: **đã hỏi nhưng chưa xác định** (`null` +
    `unknown`) và **chưa hỏi** (trường tuỳ chọn vắng hẳn). Dùng `""` làm sentinel thì lẫn với câu
    trả lời rỗng hợp lệ; dùng `"chưa rõ"` thì dính vào mọi so khớp và tìm kiếm. Bài này khoá quy ước
    lại để nó không trôi mất khi có người thêm đường ghi mới.
    """
    http, store = client

    def _context(text: str) -> dict[str, Any]:
        return {
            "requester": {"id": "usr_contract"},
            "channel": "api",
            "raw_text": text,
            "language": "vi",
        }

    # Không gửi `scope` chút nào: hợp đồng bắt buộc `drug` và `event` phải có mặt, nên tầng này tự
    # điền hai trường đó ở dạng "đã hỏi nhưng chưa xác định" — `value` là `null`, không phải `""`.
    created = await http.post(
        "/api/v2/work-items",
        json={"question": "Chưa rõ loại thuốc, mới chỉ có biến cố.", "context": _context("Chưa rõ loại thuốc.")},
        headers=_headers("investigator", "usr_contract"),
    )
    assert created.status_code == 201, created.text
    _assert_matches("WorkItem", created.json())
    scope = created.json()["scope"]
    assert scope["drug"] == {"value": None, "resolution": "unknown"}, scope["drug"]
    assert scope["event"] == {"value": None, "resolution": "unknown"}, scope["event"]

    # Đã xác định thì `value` là chuỗi thật, và `resolution` nói rõ nguồn.
    confirmed = await http.post(
        "/api/v2/work-items",
        json={
            "question": "Metformin có gây nhiễm toan lactic không?",
            "context": _context("Metformin có gây nhiễm toan lactic không?"),
            # Gửi `scope` thì phải gửi **cả hai** trường bắt buộc, kể cả trường chưa biết: hợp đồng
            # khai `scope.required = ["drug", "event"]`, nên "chưa biết thuốc" vẫn phải nói ra.
            "scope": {
                "drug": {"value": None, "resolution": "unknown"},
                "event": {"value": "nhiễm toan lactic", "resolution": "confirmed"},
            },
        },
        headers=_headers("investigator", "usr_contract"),
    )
    assert confirmed.status_code == 201, confirmed.text
    confirmed_scope = confirmed.json()["scope"]
    _assert_matches("WorkItem", confirmed.json())
    assert confirmed_scope["event"] == {"value": "nhiễm toan lactic", "resolution": "confirmed"}
    assert confirmed_scope["drug"] == {"value": None, "resolution": "unknown"}

    # Không có giá trị sentinel nào lọt vào `value`, và trường tuỳ chọn chưa biết thì vắng hẳn.
    for scope_document in (scope, confirmed_scope):
        for field in ("drug", "event"):
            value = scope_document[field]["value"]
            assert value is None or (isinstance(value, str) and value.strip() != ""), scope_document[field]
            assert value not in ("chưa rõ", "unknown", "N/A", "-"), scope_document[field]
            assert "source" not in scope_document[field], scope_document[field]
            assert "evidence_ref" not in scope_document[field], scope_document[field]

    # Và `""` gửi lên bị từ chối thẳng, thay vì được nhận rồi ngầm hiểu là "chưa rõ".
    rejected = await http.post(
        "/api/v2/work-items",
        json={
            "question": "Câu hỏi có phạm vi rỗng.",
            "context": _context("Câu hỏi có phạm vi rỗng."),
            "scope": {"drug": {"value": "", "resolution": "confirmed"}},
        },
        headers=_headers("investigator", "usr_contract"),
    )
    assert rejected.status_code == 422, rejected.text


@pytest.mark.asyncio
async def test_the_old_api_keeps_the_exact_shape_of_its_mvp_errors(client):
    """``/api/v1`` phải không đổi **gì**, kể cả những chỗ dễ đổi lây khi tách envelope.

    Lỗi ``MvpError`` của đường cũ trước đây chỉ có ``{"error": {...}}``, không có khoá phẳng. Khi
    hợp nhất bốn handler về một đường, dùng chung envelope rộng sẽ lặng lẽ thêm bốn khoá vào một API
    đang chạy — không vỡ bài kiểm nào, nhưng là một thay đổi API không ai công bố.
    """
    http, _ = client
    # 404 của đường cũ là ``StarletteHTTPException``: giữ khoá phẳng như trước.
    routing_404 = await http.get("/api/v1/khong-ton-tai", headers=_headers("investigator"))
    assert routing_404.status_code == 404, routing_404.text
    assert "code" in routing_404.json() and "message" in routing_404.json()

    # 401 của đường cũ là ``MvpError``: chỉ ``{"error": {...}}``, đúng như trước.
    anonymous = await http.get("/api/v1/investigations")
    assert anonymous.status_code == 401, anonymous.text
    body = anonymous.json()
    assert set(body) == {"error"}, body
    assert body["error"]["code"] == "unauthorized"
    assert "retryable" in body["error"]
