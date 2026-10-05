"""Thử mô hình thật (live) cho MVP — chạy tay, KHÔNG thuộc bộ test mặc định.

Mục đích: xác nhận cấu hình mô hình trong ``.env`` thật sự gọi được provider và cổng
``LLMGateway`` ghi nhận usage đúng, trước khi ghép với connector thật của Người 1.

    # .env cần GEMINI_API_KEY / OPENAI_API_KEY (và MODEL_NAME nếu provider yêu cầu)
    python scripts/live_model_smoke.py
    python scripts/live_model_smoke.py --claim "metformin gây lactic acidosis."

Script chỉ đọc cấu hình và gọi mạng; không ghi vào DB của cuộc điều tra nào.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, Field  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.models.schemas import BudgetState, ClaimInput, NormalizedClaim  # noqa: E402
from src.services.errors import MvpError  # noqa: E402
from src.services.llm import LLMGateway, TransportProvider  # noqa: E402
from src.vmec import DomainError  # noqa: E402

SYSTEM = (
    "Bạn là trợ lý chuẩn hóa claim an toàn thuốc. Chỉ trả JSON theo schema, "
    "không suy diễn quan hệ nhân quả và không bịa số liệu."
)

PROMPT = (
    "Chuẩn hóa claim sau thành JSON đúng schema (giữ nguyên khóa tiếng Anh, "
    "không thêm khóa lạ). Trường không suy ra được thì để null và ghi tên trường "
    "vào unknowns.\nSchema: {schema}\nClaim: {claim}\n"
)


class Probe(BaseModel):
    """Schema tối thiểu để thử structured output."""

    ok: bool = True
    summary: str = Field(min_length=1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Thử mô hình thật qua LLMGateway của MVP.")
    parser.add_argument("--claim", default="metformin gây lactic acidosis ở người suy thận.")
    args = parser.parse_args()

    settings = get_settings()
    print(f"provider cấu hình: {settings.model_provider} · model: {settings.model_name or '(mặc định)'}")
    print(f"có khóa: gemini={bool(settings.gemini_api_key)} openai={bool(settings.openai_api_key)}")

    gateway = LLMGateway(TransportProvider())
    budget = BudgetState()
    claim = ClaimInput(claim_text=args.claim, drug="metformin", event="lactic acidosis")

    print("\n[1] Structured output đúng schema (NormalizedClaim)")
    try:
        normalized = gateway.complete_model(
            "normalize_claim",
            PROMPT.format(
                schema=json.dumps(NormalizedClaim.model_json_schema(), ensure_ascii=False),
                claim=claim.claim_text,
            ),
            NormalizedClaim,
            system=SYSTEM,
            budget=budget,
        )
    except (DomainError, MvpError) as exc:
        status = getattr(exc, "status", 502)
        print(f"  LỖI provider: {status} {exc.code} — {exc.message}")
        return 2
    print(f"  drug_ingredient={normalized.drug_ingredient!r} event={normalized.event_term!r}")
    print(f"  unknowns={normalized.unknowns} ambiguities={normalized.ambiguities}")

    print("\n[2] Structured output sai schema → sửa 1 lần (Probe)")
    probe = gateway.complete_model(
        "probe_json",
        "Trả JSON {\"ok\": true, \"summary\": \"<một câu mô tả claim>\"} cho claim: " + claim.claim_text,
        Probe,
        system=SYSTEM,
        budget=budget,
        reserve=False,
    )
    print(f"  ok={probe.ok} summary={probe.summary[:80]!r}")

    print("\n[3] Sổ usage")
    ledger = gateway.ledger
    print(f"  lượt gọi={ledger.llm_calls} input={ledger.input_tokens} output={ledger.output_tokens} repairs={ledger.repairs}")
    for task, usage in ledger.by_task.items():
        print(f"   - {task}: {usage.calls} lượt · in={usage.input_tokens} out={usage.output_tokens}")
    print(f"  budget: calls={budget.llm_calls} in={budget.input_tokens} out={budget.output_tokens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
