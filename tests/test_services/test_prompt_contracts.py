"""Test hợp đồng prompt (P11): manifest ↔ tệp prompt ↔ schema ↔ danh sách hành động cho phép."""

from __future__ import annotations

import json

import pytest

from src.models.schemas import PlannerActionKind
from src.services.prompts import (
    MANIFEST_PATH,
    PROMPT_DIR,
    PromptError,
    load_manifest,
    load_prompt,
    prompt_hash,
    render_user,
    resolve_schema,
)


def test_manifest_declares_every_task_with_existing_files():
    manifest = load_manifest()
    assert manifest, "manifest phải có ít nhất một tác vụ"
    for task, spec in manifest.items():
        assert (PROMPT_DIR / spec.system_file).exists(), task
        assert (PROMPT_DIR / spec.user_file).exists(), task
        assert spec.version
        assert spec.description


def test_prompt_files_and_version_produce_a_stable_hash():
    prompt = load_prompt("plan")
    again = load_prompt("plan")

    assert prompt.hash == again.hash
    assert len(prompt.hash) == 32
    assert prompt.hash != prompt_hash("plan", "9.9.9", prompt.system, prompt.user_template)


def test_every_template_uses_exactly_the_declared_payload_keys():
    for task, spec in load_manifest().items():
        prompt = load_prompt(task)  # ném PromptError nếu template/manifest lệch nhau
        assert prompt.spec.payload_keys == spec.payload_keys
        sample = {key: "giá trị" for key in spec.payload_keys}
        rendered = render_user(prompt, sample)
        assert rendered.strip()
        assert "{" not in rendered  # mọi khóa đã được điền


def test_output_schemas_resolve_to_pydantic_models():
    for task, spec in load_manifest().items():
        model = resolve_schema(spec.output_schema)
        assert hasattr(model, "model_json_schema"), task


def test_allowed_values_match_the_real_enum():
    spec = load_manifest()["plan"]
    schema = resolve_schema(spec.output_schema)
    field = schema.model_fields["action"]

    assert set(spec.allowed_values["action"]) == {item.value for item in field.annotation}  # type: ignore[union-attr]
    assert set(spec.allowed_values["action"]) <= {item.value for item in PlannerActionKind}


def test_evidence_ref_fields_exist_on_their_schemas():
    for task, spec in load_manifest().items():
        if spec.evidence_refs is None:
            continue
        schema = resolve_schema(spec.output_schema)
        root_field = spec.evidence_refs.field.split(".")[0]
        assert root_field in schema.model_fields, task


def test_manifest_is_valid_json_and_has_no_orphan_task():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(raw["tasks"]) == set(load_manifest())
    for name in raw["tasks"]:
        assert load_prompt(name).task == name


def test_unknown_task_raises_prompt_error():
    with pytest.raises(PromptError):
        load_prompt("không-tồn-tại")


def test_render_user_rejects_extra_and_missing_keys():
    prompt = load_prompt("plan")

    with pytest.raises(PromptError):
        render_user(prompt, {"claim_summary": "c"})
    with pytest.raises(PromptError):
        render_user(prompt, {**{key: "x" for key in prompt.spec.payload_keys}, "lạ": "x"})
