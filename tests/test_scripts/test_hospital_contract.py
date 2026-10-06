"""Kiểm thử hợp đồng hospital-v2: lược đồ, ví dụ, OpenAPI và tính đồng bộ với MVP.

Không bài nào gọi mạng. Điểm quan trọng: hợp đồng mới phải *additive* — các enum dùng
chung với MVP (`src/models/schemas.py`) phải trùng khớp, nếu lệch là test đỏ.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from src.models import schemas as mvp

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "docs" / "spec" / "hospital-v2"
SCHEMAS_PATH = SPEC_DIR / "schemas.json"
OPENAPI_PATH = SPEC_DIR / "openapi.json"
EXAMPLES_DIR = SPEC_DIR / "examples"
INDEX_PATH = EXAMPLES_DIR / "index.json"

ENTITY_DEFS = [
    "RequestContext",
    "WorkItem",
    "InvestigationLink",
    "EvidenceBundle",
    "ProfessionalResponse",
    "FollowUp",
    "VersionRef",
    "ReviewRef",
]


@pytest.fixture(scope="module")
def schemas() -> dict:
    return json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def openapi() -> dict:
    return json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def index() -> list[dict]:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _validate(schemas: dict, def_name: str, instance: dict) -> None:
    schema = {"$ref": f"#/$defs/{def_name}", "$defs": schemas["$defs"]}
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: e.path)
    assert not errors, "; ".join(f"{list(e.path)}: {e.message}" for e in errors)


def _walk_refs(node, found: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.append(value)
            else:
                _walk_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_refs(item, found)


# ------------------------------------------------------------------ lược đồ
def test_schemas_file_is_a_valid_json_schema(schemas: dict) -> None:
    Draft202012Validator.check_schema(schemas)
    assert schemas["x-contract-status"] == "proposed_not_implemented"
    for name in ENTITY_DEFS:
        assert name in schemas["$defs"], name


def test_examples_validate_against_their_definitions(schemas: dict, index: list[dict]) -> None:
    assert index, "index.json rỗng"
    for entry in index:
        path = EXAMPLES_DIR / entry["file"]
        assert path.exists(), entry["file"]
        _validate(schemas, entry["def"], json.loads(path.read_text(encoding="utf-8")))


def test_examples_cover_unknown_draft_error_and_abstract_only(schemas: dict, index: list[dict]) -> None:
    instances = {
        entry["file"]: json.loads((EXAMPLES_DIR / entry["file"]).read_text(encoding="utf-8")) for entry in index
    }
    draft = [row for row in instances.values() if row.get("work_status") == "draft"]
    assert draft and draft[0]["unknowns"], "thiếu ví dụ nháp còn trường unknown"
    assert any(row.get("status") == "draft" for row in instances.values()), "thiếu ví dụ phiếu trả lời nháp"
    bundles = [row for row in instances.values() if "source_errors" in row and row["source_errors"]]
    assert bundles, "thiếu ví dụ lỗi nguồn"
    assert any(item["retrieval"] == "abstract_only" for row in instances.values() for item in row.get("items", [])), (
        "thiếu ví dụ bằng chứng chỉ có tóm tắt"
    )
    assert any("version_conflict" == (row.get("error") or {}).get("code") for row in instances.values()), (
        "thiếu ví dụ lỗi xung đột phiên bản"
    )


def test_work_item_keeps_three_statuses_separate(schemas: dict) -> None:
    work_item = schemas["$defs"]["WorkItem"]
    assert {"work_status", "run_status", "review_status"} <= set(work_item["required"])
    assert "status" not in work_item["properties"], "WorkItem không được gộp ba trạng thái vào một trường"
    assert schemas["$defs"]["WorkStatus"]["enum"] == [
        "draft",
        "accepted",
        "in_progress",
        "awaiting_information",
        "awaiting_review",
        "completed",
        "cancelled",
    ]


def test_unknown_is_a_first_class_value(schemas: dict) -> None:
    assert "unknown" in schemas["$defs"]["ScopeField"]["properties"]["resolution"]["enum"]
    assert "unknown" in schemas["$defs"]["EvidenceItem"]["properties"]["scope_match"]["enum"]
    unknown = schemas["$defs"]["UnknownField"]
    assert {"field", "reason", "needs_confirmation"} <= set(unknown["required"])


# ------------------------------------------------------------------ đồng bộ với MVP
def test_shared_enums_match_the_mvp_schemas(schemas: dict) -> None:
    defs = schemas["$defs"]
    assert defs["EvidenceBundle"]["properties"]["assessment_status"]["enum"] == [s.value for s in mvp.AssessmentStatus]
    assert defs["EvidenceItem"]["properties"]["stance"]["enum"] == [s.value for s in mvp.Stance]
    assert defs["EvidenceItem"]["properties"]["evidence_type"]["enum"] == [s.value for s in mvp.EvidenceType]
    assert defs["ApiError"]["properties"]["error"]["properties"]["code"]["enum"] == [s.value for s in mvp.ErrorCode]
    review_actions = set(defs["ReviewRef"]["properties"]["action"]["enum"])
    assert {s.value for s in mvp.ReviewAction} <= review_actions, "ReviewRef.action phải giữ mọi giá trị MVP"
    assert "request_changes" in review_actions
    run_values = set(defs["RunStatusRef"]["enum"])
    assert {s.value for s in mvp.RunStatus} <= run_values, "RunStatusRef phải phản chiếu RunStatus của MVP"
    assert "not_started" in run_values
    gap_values = set(defs["Gap"]["properties"]["kind"]["enum"])
    assert {s.value for s in mvp.GapKind} <= gap_values, "Gap.kind chỉ được thêm giá trị, không bỏ giá trị MVP"


# ------------------------------------------------------------------ OpenAPI
def test_openapi_refs_resolve(schemas: dict, openapi: dict) -> None:
    refs: list[str] = []
    _walk_refs(openapi, refs)
    assert refs
    external = [ref for ref in refs if not ref.startswith("#/") and "#" in ref]
    assert external, "OpenAPI phải tham chiếu schemas.json để giữ một nguồn sự thật"
    for ref in external:
        file_part, _, pointer = ref.partition("#")
        assert file_part == "schemas.json", ref
        target = schemas
        for token in pointer.strip("/").split("/"):
            assert token in target, f"{ref} không tồn tại trong schemas.json"
            target = target[token]
    for ref in [item for item in refs if item.startswith("#/")]:
        target = openapi
        for token in ref.strip("#/").split("/"):
            assert token in target, f"{ref} không tồn tại trong openapi.json"
            target = target[token]


def test_openapi_operations_are_complete_and_use_valid_examples(openapi: dict, index: list[dict]) -> None:
    index_by_file = {entry["file"]: entry for entry in index}
    operations = 0
    for path, methods in openapi["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            operations += 1
            assert operation.get("operationId"), f"{method} {path} thiếu operationId"
            assert operation.get("responses"), f"{method} {path} thiếu responses"
            payloads = []
            if "requestBody" in operation:
                payloads.append(operation["requestBody"]["content"]["application/json"])
            for status, response in operation["responses"].items():
                if status.startswith("2"):
                    payloads.append(response.get("content", {}).get("application/json", {}))
            assert payloads, f"{method} {path} không có schema"
            for payload in payloads:
                schema_ref = payload["schema"]["$ref"]
                def_name = schema_ref.rsplit("/", 1)[-1]
                assert def_name in json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))["$defs"], schema_ref
                examples = payload.get("examples") or {}
                for example_ref in [item["$ref"] for item in examples.values()]:
                    file_name = example_ref.rsplit("/", 1)[-1]
                    assert file_name in index_by_file, example_ref
                    assert index_by_file[file_name]["def"] == def_name, f"{file_name} khai báo sai def cho {schema_ref}"
    assert operations >= 9


def test_openapi_declares_additive_namespace(openapi: dict) -> None:
    assert all(path.startswith("/api/v2/") for path in openapi["paths"])
    assert openapi["x-contract-status"] == "proposed_not_implemented"
