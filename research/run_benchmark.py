"""Run the frozen synthetic benchmark with real model calls and audit artifacts."""

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from research.fixtures import ResearchCase, load_cases
from research.manifest import build_manifest
from research.metrics import score
from research.runners import ACTION_SYSTEM, DIRECT_SYSTEM, EXTRACT_SYSTEM, CaseResult, run_case
from src.ai.transport import ModelResult, complete_json, selected_model, selected_provider
from src.config import Settings, get_settings
from src.vmec import DomainError


class BudgetStopError(Exception):
    pass


def require_model_key(settings: Settings) -> None:
    provider = selected_provider(settings)
    key = settings.openai_api_key if provider == "openai" else settings.gemini_api_key
    if not key or key.startswith("sk-your-"):
        raise DomainError(503, "MODEL_UNAVAILABLE", "Chưa cấu hình khóa mô hình AI.", True)
    if provider == "openai_compatible" and not settings.gemini_base_url:
        raise DomainError(422, "MODEL_CONFIG_INVALID", "Thiếu base URL cho proxy.")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _write_json(path: Path, value: dict):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def execute(
    cases: list[ResearchCase], strategies: list[str], output: Path, adapter,
    settings: Settings, *, max_calls: int | None = None, max_cost_usd: float | None = None,
    workers: int = 1,
) -> dict:
    require_model_key(settings)
    if max_calls is not None and max_calls < 0:
        raise ValueError("max_calls must be nonnegative")
    priced = settings.model_input_usd_per_million is not None and settings.model_output_usd_per_million is not None
    if max_cost_usd is not None and not priced:
        raise ValueError("USD cap requires verified provider token prices")
    if workers < 1 or workers > 8:
        raise ValueError("workers must be between 1 and 8")
    if workers > 1 and (max_calls is not None or max_cost_usd is not None):
        raise ValueError("capped runs require one worker")
    output.mkdir(parents=True, exist_ok=True)
    provider = selected_provider(settings)
    model = selected_model(settings, provider)
    dataset = build_manifest(load_cases("dev"), load_cases("test"))
    manifest = {
        **dataset, "status": "running", "started_at": datetime.now(UTC).isoformat(),
        "selected_cases": [case.case_id for case in cases], "strategies": strategies,
        "provider": provider, "requested_model": model, "returned_models": [],
        "temperature": settings.llm_temperature,
        "prompt_sha256": {"extract": _hash(EXTRACT_SYSTEM), "direct": _hash(DIRECT_SYSTEM),
                          "action": _hash(ACTION_SYSTEM)},
        "max_calls": max_calls, "max_cost_usd": max_cost_usd,
        "workers": workers,
        "pricing": {"input_usd_per_million": settings.model_input_usd_per_million,
                    "output_usd_per_million": settings.model_output_usd_per_million} if priced else "unknown",
    }
    _write_json(output / "vmec03-manifest.json", manifest)
    results: list[CaseResult] = []
    returned_models: set[str] = set()
    attempts = 0
    spent_usd = 0.0
    usage_available = True
    stopped = False
    accounting_lock = Lock()

    def checked_adapter(system: str, user: str) -> ModelResult:
        nonlocal attempts, spent_usd, usage_available
        with accounting_lock:
            if max_calls is not None and attempts >= max_calls:
                raise BudgetStopError("call cap reached")
            if max_cost_usd is not None and spent_usd >= max_cost_usd:
                raise BudgetStopError("USD cap reached")
            attempts += 1
        try:
            answer = adapter(system, user)
        except Exception:
            with accounting_lock:
                usage_available = False
            raise
        with accounting_lock:
            if priced:
                if answer.prompt_tokens is None or answer.completion_tokens is None:
                    usage_available = False
                    raise BudgetStopError("usage unavailable for priced run")
                spent_usd += (answer.prompt_tokens * settings.model_input_usd_per_million
                              + answer.completion_tokens * settings.model_output_usd_per_million) / 1_000_000
            if answer.returned_model:
                returned_models.add(answer.returned_model)
        return answer

    labels = {case.case_id: case.labels for case in cases}
    jobs = [(strategy, case) for strategy in strategies for case in cases]
    pool = ThreadPoolExecutor(max_workers=workers) if workers > 1 else None
    futures = [pool.submit(run_case, case, strategy, checked_adapter) for strategy, case in jobs] if pool else []
    try:
        with (output / "vmec03-per-case.jsonl").open("w", encoding="utf-8") as rows:
            for index, (strategy, case) in enumerate(jobs):
                if stopped:
                    result = CaseResult(case.case_id, case.group, strategy, "incomplete", [], 0, 0, 0, 0, None, 0.0, "NOT_RUN_AFTER_STOP")
                else:
                    result = futures[index].result() if pool else run_case(case, strategy, checked_adapter)
                    if priced and usage_available:
                        result.cost_usd = round((result.prompt_tokens * settings.model_input_usd_per_million
                                                 + result.completion_tokens * settings.model_output_usd_per_million) / 1_000_000, 8)
                    if result.error in ("BudgetStopError", "MODEL_PERMISSION_DENIED", "MODEL_UNAVAILABLE", "MODEL_CONFIG_INVALID"):
                        stopped = True
                results.append(result)
                rows.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
                rows.flush()
                print(f"{strategy} {case.case_id}: {result.status} ({result.error or result.model_calls})", flush=True)
                manifest["completed_rows"] = len(results)
                manifest["returned_models"] = sorted(returned_models)
                _write_json(output / "vmec03-manifest.json", manifest)
    finally:
        if pool:
            pool.shutdown(wait=True)
    by_strategy = {strategy: score([r for r in results if r.strategy == strategy], labels) for strategy in strategies}
    _write_json(output / "vmec03-aggregate.json", by_strategy)
    manifest["status"] = "completed" if all(r.status == "completed" for r in results) else "incomplete"
    manifest["finished_at"] = datetime.now(UTC).isoformat()
    manifest["model_call_attempts"] = attempts
    manifest["cost_usd"] = round(spent_usd, 8) if priced and usage_available else None
    manifest["returned_models"] = sorted(returned_models)
    _write_json(output / "vmec03-manifest.json", manifest)
    report = [
        "# Benchmark tổng hợp VMEC-03", "",
        f"Trạng thái: **{manifest['status']}**. Bộ dữ liệu: `{dataset['dataset_version']}`. Nhà cung cấp: `{provider}`. "
        f"Mô hình yêu cầu: `{model}`. ID trả về: `{', '.join(sorted(returned_models)) or 'N/A'}`.", "",
        "Đây là kiểm tra hành vi phần mềm trên ca tổng hợp do nhóm tự soạn. Nhãn chưa được bác sĩ duyệt; "
        "kết quả không chứng minh an toàn lâm sàng hay tiết kiệm thời gian.", "",
        "| Chiến lược | Hoàn tất / tổng số | Precision vấn đề micro | Recall vấn đề micro | Đóng sai | Chuyển giao | Lượt gọi | Token | Chi phí USD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy, metrics in by_strategy.items():
        report.append(f"| {strategy} | {metrics['cases_completed']} / {metrics['cases_total']} | "
                      f"{metrics['issue_precision_micro']} | {metrics['issue_recall_micro']} | "
                      f"{metrics['false_closure_count']} | {metrics['handed_off_count']} | "
                      f"{metrics['model_calls']} | {metrics['total_tokens']} | "
                      f"{metrics['cost_usd'] if metrics['cost_usd'] is not None else 'chưa rõ'} |")
    report.extend(["", "| Chiến lược | Độ chính xác trường | Có trích dẫn | Trích dẫn hỗ trợ trường | Tỷ lệ xử lý xong | Câu hỏi lặp | Nguồn đến muộn hiển thị | Thời gian (giây) |",
                   "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for strategy, metrics in by_strategy.items():
        report.append(f"| {strategy} | {metrics['field_accuracy']} ({metrics['field_correct']}/{metrics['field_total']}) | "
                      f"{metrics['citation_existence']} | {metrics['citation_support']} | "
                      f"{metrics['resolved_coverage']} | {metrics['repeated_questions']} | "
                      f"{metrics['delayed_source_visibility']} | {metrics['latency_seconds']} |")
    report.extend(["", "Số đếm và mẫu số chi tiết: `vmec03-aggregate.json`. "
                   "Mọi dòng chưa hoàn tất được giữ trong `vmec03-per-case.jsonl`. Mẫu số bằng 0 được ghi N/A. "
                   "Chi phí USD chưa rõ nếu chưa cấu hình đơn giá token đã kiểm chứng. "
                   "Giới hạn chi phí được kiểm tra trước mỗi lượt gọi mới; một lượt vẫn có thể vượt giới hạn vì chưa biết trước số token đầu ra.", ""])
    (output / "vmec03-report.md").write_text("\n".join(report), encoding="utf-8")
    return {"status": manifest["status"], "by_strategy": by_strategy, "rows": len(results), "attempts": attempts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--strategies", nargs="+", choices=("A", "B1", "B2"), default=["A", "B1", "B2"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-cost-usd", type=float)
    parser.add_argument("--workers", type=int, default=1, help="Concurrent independent cases (1-8; requires no optional cap)")
    args = parser.parse_args()
    settings = get_settings()
    cases = load_cases(args.split)
    summary = execute(cases, args.strategies, args.output, complete_json, settings,
                      max_calls=args.max_calls, max_cost_usd=args.max_cost_usd, workers=args.workers)
    print(json.dumps({"status": summary["status"], "rows": summary["rows"], "attempts": summary["attempts"]}))
    return 0 if summary["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
