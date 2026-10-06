"""LLM Gateway cho MVP (M02, P11): structured output, mock offline, đếm token và dự phòng ngân sách.

Nguyên tắc (P11):
  * Mọi output của LLM phải là JSON khớp một Pydantic schema; sai định dạng thì sửa **tối đa 1 lần**.
  * Tách kênh: ``system`` (chính sách của hệ thống) ≠ ``payload`` (code truyền vào theo manifest) ≠
    ``untrusted`` (văn bản nguồn, chỉ nằm trong khối được đánh dấu). Nội dung nguồn không thể sửa
    nhiệm vụ, schema hay danh sách hành động — danh sách đó do manifest quy định.
  * Ngân sách được **đặt trước** khi gọi (số lượt + token ước lượng); sau khi trả lời mới ghi số thật.
    Khi không biết số token thật (lỗi provider hoặc provider không trả usage) thì giữ nguyên phần
    đặt trước — không hoàn ngân sách một cách mù quáng.
  * Test offline dùng ``MockProvider`` — không gọi mạng, không tốn token thật.
  * Hai lượt gọi cuối được **giữ dự phòng** cho bước tạo hồ sơ/abstain (``reserve=True`` theo mặc định).
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Iterable
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, Field, ValidationError

from src.models.schemas import RESERVED_LLM_CALLS_FOR_DOSSIER, BudgetState
from src.services.errors import budget_exhausted, invalid_request, llm_format_error, model_unavailable
from src.services.prompts import (
    MAX_PROMPT_CHARS,
    LoadedPrompt,
    UntrustedChunk,
    load_prompt,
    render_untrusted,
    render_user,
    resolve_schema,
)

ModelT = TypeVar("ModelT", bound=BaseModel)

REPAIR_INSTRUCTION = (
    "Kết quả trước không phải JSON hợp lệ theo schema. Chỉ trả về DUY NHẤT một JSON object đúng schema, "
    "không thêm văn bản, không thêm markdown."
)

#: Trần ước lượng token đầu ra cho một lượt gọi (đặt trước, đối chiếu sau).
MAX_OUTPUT_TOKEN_RESERVE = 1024
#: Số ký tự ước lượng cho một token (xấp xỉ, dùng cho phần đặt trước).
CHARS_PER_TOKEN = 4


class LLMResponse(BaseModel):
    """Phản hồi thô của provider kèm số token."""

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "unknown"
    usage_known: bool = True


class LLMCallMetadata(BaseModel):
    """Metadata nội bộ của một lượt gọi (không trả ra API công khai)."""

    task: str
    prompt_version: str = "ad-hoc"
    prompt_hash: str = ""
    model: str = "unknown"
    repair: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    #: Thời gian gọi mô hình thật (ms). Trước đây không có nên mọi bước hiện 0.
    duration_ms: int = 0


class LLMProvider(Protocol):
    """Nhà cung cấp LLM (thật hoặc mock)."""

    name: str

    def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        json_schema: dict[str, Any] | None,
        untrusted: str = "",
    ) -> LLMResponse: ...


class MockProvider:
    """Provider offline: trả lời theo kịch bản ``task -> payload``.

    ``responses`` nhận:
      * ``str`` — trả nguyên văn (dùng để test JSON hỏng);
      * ``dict``/``list`` — được ``json.dumps`` lại;
      * ``callable(prompt, system) -> str | dict`` — sinh động theo prompt.
    """

    name = "mock"

    def __init__(self, responses: dict[str, Any] | None = None, *, model: str = "mock-model"):
        self.responses = responses or {}
        self.model = model
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        json_schema: dict[str, Any] | None,
        untrusted: str = "",
    ) -> LLMResponse:
        self.calls.append({"task": task, "prompt": prompt, "system": system, "untrusted": untrusted})
        key = task if task in self.responses else task.split(":")[0]
        if key not in self.responses:
            raise AssertionError(f"MockProvider chưa có kịch bản cho task '{task}' (offline test phải cấu hình trước).")
        value = self.responses[key]
        if callable(value):
            value = value(prompt, system)
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return LLMResponse(
            text=text,
            input_tokens=max(1, len(prompt) // CHARS_PER_TOKEN),
            output_tokens=max(1, len(text) // CHARS_PER_TOKEN),
            model=self.model,
        )


class TransportProvider:
    """Provider thật, dùng ``src.ai.transport.complete_json`` (OpenAI / openai_compatible / Gemini)."""

    name = "transport"

    def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        json_schema: dict[str, Any] | None,
        untrusted: str = "",
    ) -> LLMResponse:
        from src.ai.transport import complete_json
        from src.config import get_settings
        from src.vmec import DomainError

        user = f"{prompt}\n\n{untrusted}" if untrusted else prompt
        try:
            result = complete_json(system, user, get_settings())
        except DomainError as exc:  # pragma: no cover - cần mạng
            raise model_unavailable(exc.message) from None
        known = bool(result.prompt_tokens) or bool(result.completion_tokens)
        return LLMResponse(
            text=json.dumps(result.data, ensure_ascii=False),
            input_tokens=result.prompt_tokens or 0,
            output_tokens=result.completion_tokens or 0,
            model=result.returned_model or result.requested_model,
            usage_known=known,
        )


class TaskUsage(BaseModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class UsageLedger(BaseModel):
    """Sổ ghi lượt gọi và token theo từng tác vụ."""

    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    repairs: int = 0
    unknown_usage_calls: int = 0
    by_task: dict[str, TaskUsage] = Field(default_factory=dict)
    records: list[LLMCallMetadata] = Field(default_factory=list)

    def record(self, task: str, response: LLMResponse) -> None:
        self.llm_calls += 1
        self.input_tokens += response.input_tokens
        self.output_tokens += response.output_tokens
        usage = self.by_task.setdefault(task, TaskUsage())
        usage.calls += 1
        usage.input_tokens += response.input_tokens
        usage.output_tokens += response.output_tokens

    def record_call(self, metadata: LLMCallMetadata) -> None:
        self.records.append(metadata)

    def last(self, task: str | None = None) -> LLMCallMetadata | None:
        for item in reversed(self.records):
            if task is None or item.task == task:
                return item
        return None


class _Reservation(BaseModel):
    """Phần ngân sách đặt trước cho một lượt gọi."""

    task: str
    key: str
    input_tokens: int
    output_tokens: int


def _collect_refs(value: Any, parts: list[str]) -> list[str]:
    """Thu ID bằng chứng theo đường dẫn có thể đi qua danh sách (``sections.evidence_ids``)."""
    if not parts:
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return [str(value)] if value else []
    if isinstance(value, list):
        collected: list[str] = []
        for item in value:
            collected.extend(_collect_refs(item, parts))
        return collected
    child = getattr(value, parts[0], None)
    if child is None:
        return []
    return _collect_refs(child, parts[1:])


def extract_json_object(text: str) -> dict[str, Any]:
    """Lấy JSON object đầu tiên trong text (chấp nhận code fence)."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lower().startswith("json"):
            candidate = candidate[4:]
        candidate = candidate.strip()
    try:
        data = json.loads(candidate)
    except ValueError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("Không tìm thấy JSON object trong output") from None
        data = json.loads(candidate[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Output phải là JSON object")
    return data


class LLMGateway:
    """Cổng duy nhất để gọi LLM trong MVP."""

    def __init__(self, provider: LLMProvider | None = None, *, ledger: UsageLedger | None = None):
        self.provider = provider or TransportProvider()
        self.ledger = ledger or UsageLedger()

    # ------------------------------------------------------------------ API chính (P11)

    def invoke(
        self,
        task: str,
        payload: dict[str, Any],
        output_schema: type[ModelT] | None = None,
        *,
        budget: BudgetState | None = None,
        untrusted: Iterable[UntrustedChunk | str] = (),
        evidence_ids: Iterable[str] | None = None,
        reserve: bool = True,
        context: dict[str, Any] | None = None,
    ) -> ModelT:
        """Gọi LLM theo prompt đã đăng ký trong manifest và trả về output đã validate."""
        prompt = load_prompt(task)
        schema = output_schema or resolve_schema(prompt.spec.output_schema)
        user_text = render_user(prompt, payload)
        untrusted_text = render_untrusted(untrusted, limit=prompt.spec.untrusted_char_limit)
        self._check_prompt_size(task, user_text, untrusted_text, context=context)

        reservation = self._reserve(
            budget,
            task,
            prompt_chars=len(user_text) + len(untrusted_text),
            max_output_chars=prompt.spec.max_output_chars,
            reserve=reserve,
        )
        response = self._call(
            task,
            system=prompt.system,
            prompt=user_text,
            untrusted=untrusted_text,
            schema=schema,
            budget=budget,
            reservation=reservation,
            prompt_version=prompt.spec.version,
            prompt_hash=prompt.hash,
        )
        try:
            return self._validate(response.text, schema, prompt, evidence_ids)
        except (ValidationError, ValueError) as exc:
            return self._repair(
                task=task,
                prompt=prompt,
                schema=schema,
                previous=response.text,
                error=exc,
                budget=budget,
                reservation=reservation,
                evidence_ids=evidence_ids,
                context=context,
            )

    # ------------------------------------------------------------------ API tương thích (M02)

    def complete_model(
        self,
        task: str,
        prompt: str,
        schema: type[ModelT],
        *,
        system: str = "",
        budget: BudgetState | None = None,
        reserve: bool = True,
        context: dict[str, Any] | None = None,
    ) -> ModelT:
        """Gọi LLM với prompt tự do (giữ cho luồng cũ và script thử mô hình); sai định dạng thì sửa 1 lần."""
        reservation = self._reserve(
            budget,
            task,
            prompt_chars=len(prompt),
            max_output_chars=len(prompt) * 2,
            reserve=reserve,
        )
        response = self._call(
            task,
            system=system,
            prompt=prompt,
            untrusted="",
            schema=schema,
            budget=budget,
            reservation=reservation,
        )
        try:
            return self._parse(response.text, schema)
        except (ValidationError, ValueError) as exc:
            self.ledger.repairs += 1
            repair_prompt = self._repair_prompt(schema, response.text, exc)
            repair_reservation = self._reserve(
                budget,
                f"{task}:repair",
                prompt_chars=len(repair_prompt),
                max_output_chars=len(repair_prompt) * 2,
                reserve=reserve,
            )
            repaired = self._call(
                f"{task}:repair",
                system=system,
                prompt=repair_prompt,
                untrusted="",
                schema=schema,
                budget=budget,
                reservation=repair_reservation,
            )
            try:
                return self._parse(repaired.text, schema)
            except (ValidationError, ValueError) as final_exc:
                raise llm_format_error(
                    "LLM trả sai định dạng sau 1 lần sửa.",
                    {"task": task, "error": str(final_exc), "context": context or {}},
                ) from None

    def reconcile(
        self,
        budget: BudgetState | None,
        task: str,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        """Đối chiếu phần đặt trước còn treo của ``task`` khi đã biết số token thật."""
        if budget is None:
            return
        reservation = self._take_reservation(budget, task)
        if reservation is None:
            return
        self._settle_actual(budget, input_tokens=input_tokens, output_tokens=output_tokens)

    # ------------------------------------------------------------------ nội bộ

    def _repair(
        self,
        *,
        task: str,
        prompt: LoadedPrompt,
        schema: type[ModelT],
        previous: str,
        error: Exception,
        budget: BudgetState | None,
        reservation: _Reservation | None,
        evidence_ids: Iterable[str] | None,
        context: dict[str, Any] | None,
    ) -> ModelT:
        """Sửa output sai định dạng đúng một lần; không gửi lại nội dung nguồn không tin cậy."""
        self.ledger.repairs += 1
        repair_prompt = self._repair_prompt(schema, previous, error)
        repair_reservation = self._reserve(
            budget,
            f"{task}:repair",
            prompt_chars=len(repair_prompt),
            max_output_chars=prompt.spec.max_output_chars,
            reserve=True,
        )
        repaired = self._call(
            f"{task}:repair",
            system=prompt.system,
            prompt=repair_prompt,
            untrusted="",
            schema=schema,
            budget=budget,
            reservation=repair_reservation,
            prompt_version=prompt.spec.version,
            prompt_hash=prompt.hash,
        )
        try:
            return self._validate(repaired.text, schema, prompt, evidence_ids)
        except (ValidationError, ValueError) as final_exc:
            raise llm_format_error(
                "LLM trả sai định dạng sau 1 lần sửa.",
                {"task": task, "error": str(final_exc), "context": context or {}},
            ) from None

    @staticmethod
    def _repair_prompt(schema: type[BaseModel], previous: str, error: Exception) -> str:
        return (
            f"{REPAIR_INSTRUCTION}\n\nLỗi: {error}\n\nSchema: "
            f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}\n\nOutput trước đó:\n{previous}"
        )

    def _call(
        self,
        task: str,
        *,
        system: str,
        prompt: str,
        untrusted: str,
        schema: type[BaseModel],
        budget: BudgetState | None,
        reservation: _Reservation | None,
        prompt_version: str = "ad-hoc",
        prompt_hash: str = "",
    ) -> LLMResponse:
        started = time.monotonic()
        try:
            response = self.provider.complete(
                task=task,
                system=system,
                prompt=prompt,
                json_schema=schema.model_json_schema(),
                untrusted=untrusted,
            )
        except Exception:
            # Không biết token thật đã dùng ⇒ giữ nguyên phần đặt trước (bảo thủ).
            self.ledger.unknown_usage_calls += 1
            raise
        self.ledger.record(task, response)
        self.ledger.record_call(
            LLMCallMetadata(
                task=task,
                prompt_version=prompt_version,
                prompt_hash=prompt_hash,
                model=response.model,
                repair=task.endswith(":repair"),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        )
        if reservation is not None and budget is not None:
            if response.usage_known:
                self._take_reservation(budget, reservation.task)
                self._settle_actual(
                    budget, input_tokens=response.input_tokens, output_tokens=response.output_tokens
                )
            else:
                self.ledger.unknown_usage_calls += 1
        return response

    def _reserve(
        self,
        budget: BudgetState | None,
        task: str,
        *,
        prompt_chars: int,
        max_output_chars: int,
        reserve: bool,
    ) -> _Reservation | None:
        """Đặt trước 1 lượt gọi + token ước lượng; vượt trần thì chặn trước khi gọi provider."""
        if budget is None:
            return None
        limit = budget.max_llm_calls - (RESERVED_LLM_CALLS_FOR_DOSSIER if reserve else 0)
        if budget.llm_calls + 1 > limit:
            raise budget_exhausted(
                "Hết ngân sách lượt gọi LLM cho bước nghiệp vụ.",
                {"task": task, "llm_calls": budget.llm_calls, "limit": limit, "reserved": reserve},
            )
        estimate_in = max(1, math.ceil(prompt_chars / CHARS_PER_TOKEN))
        estimate_out = max(1, min(math.ceil(max_output_chars / CHARS_PER_TOKEN), MAX_OUTPUT_TOKEN_RESERVE))
        reserved_in, reserved_out = self._reserved_totals(budget)
        if budget.input_tokens + reserved_in + estimate_in > budget.max_input_tokens:
            raise budget_exhausted(
                "Hết ngân sách token đầu vào.",
                {
                    "task": task,
                    "input_tokens": budget.input_tokens,
                    "reserved": reserved_in,
                    "estimate": estimate_in,
                    "limit": budget.max_input_tokens,
                },
            )
        if budget.output_tokens + reserved_out + estimate_out > budget.max_output_tokens:
            raise budget_exhausted(
                "Hết ngân sách token đầu ra.",
                {
                    "task": task,
                    "output_tokens": budget.output_tokens,
                    "reserved": reserved_out,
                    "estimate": estimate_out,
                    "limit": budget.max_output_tokens,
                },
            )
        budget.llm_calls += 1
        key = f"{task}#{len(budget.reservations)}"
        budget.reservations[key] = estimate_in + estimate_out
        return _Reservation(task=task, key=key, input_tokens=estimate_in, output_tokens=estimate_out)

    @staticmethod
    def _reserved_totals(budget: BudgetState) -> tuple[int, int]:
        total = sum(budget.reservations.values())
        # Chỉ dùng tổng cho cả hai trần: an toàn hơn (không tách được in/out từ giá trị đã lưu).
        return total, total

    @staticmethod
    def _take_reservation(budget: BudgetState, task: str) -> _Reservation | None:
        for key in [key for key in budget.reservations if key.startswith(f"{task}#")]:
            value = budget.reservations.pop(key)
            return _Reservation(task=task, key=key, input_tokens=value, output_tokens=0)
        return None

    @staticmethod
    def _settle_actual(
        budget: BudgetState, *, input_tokens: int | None, output_tokens: int | None
    ) -> None:
        """Ghi số thật, luôn giữ bộ đếm trong trần để state còn đọc được."""
        if input_tokens:
            budget.input_tokens = min(budget.input_tokens + input_tokens, budget.max_input_tokens)
        if output_tokens:
            budget.output_tokens = min(budget.output_tokens + output_tokens, budget.max_output_tokens)
        if budget.input_tokens >= budget.max_input_tokens or budget.output_tokens >= budget.max_output_tokens:
            raise budget_exhausted(
                "Đã chạm trần token kỹ thuật.",
                {
                    "input_tokens": budget.input_tokens,
                    "output_tokens": budget.output_tokens,
                    "max_input_tokens": budget.max_input_tokens,
                    "max_output_tokens": budget.max_output_tokens,
                },
            )

    @staticmethod
    def _check_prompt_size(
        task: str, user_text: str, untrusted_text: str, *, context: dict[str, Any] | None
    ) -> None:
        total = len(user_text) + len(untrusted_text)
        if total > MAX_PROMPT_CHARS:
            raise invalid_request(
                "Prompt vượt giới hạn kích thước cho một lượt gọi.",
                {"task": task, "chars": total, "limit": MAX_PROMPT_CHARS, "context": context or {}},
            )

    @classmethod
    def _validate(
        cls,
        text: str,
        schema: type[ModelT],
        prompt: LoadedPrompt,
        evidence_ids: Iterable[str] | None,
    ) -> ModelT:
        """Schema + danh sách giá trị hợp lệ + đối chiếu ID bằng chứng (nếu manifest yêu cầu)."""
        if len(text) > prompt.spec.max_output_chars:
            raise ValueError(
                f"Output dài {len(text)} ký tự, vượt giới hạn {prompt.spec.max_output_chars} của '{prompt.task}'"
            )
        model = cls._parse(text, schema)
        for field, allowed in prompt.spec.allowed_values.items():
            value = getattr(model, field, None)
            if value is not None and str(value) not in allowed:
                raise ValueError(f"Giá trị '{value}' của trường '{field}' không nằm trong danh sách cho phép")
        spec = prompt.spec.evidence_refs
        if spec is not None:
            refs = _collect_refs(model, spec.field.split("."))
            if spec.required and not refs:
                raise ValueError(f"Thiếu '{spec.field}' bắt buộc theo manifest")
            if evidence_ids is not None:
                known = set(evidence_ids)
                unknown = [ref for ref in refs if ref not in known]
                if unknown:
                    raise ValueError(f"ID bằng chứng không tồn tại trong cuộc điều tra: {unknown}")
        return model

    @staticmethod
    def _parse(text: str, schema: type[ModelT]) -> ModelT:
        return schema.model_validate(extract_json_object(text))


# --------------------------------------------------------------------------------------
# Tương thích ngược với template cũ
# --------------------------------------------------------------------------------------


def get_llm():
    """LLM client của template MedReview cũ (giữ nguyên để không phá vỡ luồng VMEC)."""
    from langchain_openai import ChatOpenAI

    from src.config import get_settings

    settings = get_settings()
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        temperature=settings.llm_temperature,
    )
