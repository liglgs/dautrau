"""In-process runner (M02): mỗi thời điểm chỉ chạy một cuộc điều tra.

Trách nhiệm:
  * khóa một-người-một-lúc: yêu cầu mới khi đang chạy → lỗi ``runner_busy`` (429);
  * lưu state sau mỗi node và lưu ``next_stage`` **trước** khi chờ reviewer;
  * phục hồi sau restart/crash: run đang dở → ``interrupted``, giữ nguyên counters và checkpoint;
  * cấp ``RunContext`` cho executor (graph) để đọc/ghi store và gọi LLM gateway.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.models.schemas import CheckpointKind, ErrorCode, InvestigationState, RunStatus
from src.services.errors import MvpError, invalid_state, runner_busy
from src.services.llm import LLMGateway
from src.services.store import MvpStore

Executor = Callable[[InvestigationState, "RunContext"], InvestigationState]


class InvestigationCancelledError(Exception):
    """Ném khi cuộc điều tra nhận tín hiệu hủy trong lúc đang chạy."""


@dataclass
class RunContext:
    """Bối cảnh chạy được truyền vào executor/graph."""

    store: MvpStore
    gateway: LLMGateway
    runner: InProcessRunner | None = None
    notes: list[str] = field(default_factory=list)
    #: Điểm cắm cho Người 1/Người 3; None ⇒ dùng mock fixture (demo mode).
    adapters: dict[str, Any] = field(default_factory=dict)
    extractor: Any | None = None
    normalizer: Any | None = None
    dossier_builder: Any | None = None
    evidence_analyzer: Any | None = None
    scenario: dict[str, Any] | None = None
    source_factory: Callable[[Any], dict[str, Any]] | None = None

    def is_cancelled(self, investigation_id: str) -> bool:
        return self.runner is not None and self.runner.is_cancelled(investigation_id)

    def check_cancelled(self, investigation_id: str) -> None:
        if self.is_cancelled(investigation_id):
            raise InvestigationCancelledError(f"Cuộc điều tra {investigation_id} đã bị hủy.")

    def save(
        self,
        state: InvestigationState,
        *,
        event: tuple[str, str] | None = None,
        expected_version: int | None = None,
        actor: str = "agent",
    ) -> InvestigationState:
        """Lưu state sau một node (mặc định kiểm tra phiên bản hiện tại của state)."""
        self.check_cancelled(state.investigation_id)
        return self.store.save_state(
            state,
            expected_version=state.version if expected_version is None else expected_version,
            event=event,
            actor=actor,
        )

    def emit(self, investigation_id: str, kind: str, message: str = "", payload: dict[str, Any] | None = None) -> int:
        return self.store.append_event(investigation_id, kind, message, payload)

    def pause_for_review(
        self,
        state: InvestigationState,
        *,
        checkpoint: CheckpointKind,
        next_stage: str,
        message: str = "",
    ) -> InvestigationState:
        """Lưu ``next_stage`` + checkpoint TRƯỚC khi chờ reviewer."""
        paused = state.model_copy(
            update={
                "run_status": RunStatus.WAITING_FOR_REVIEW,
                "checkpoint": checkpoint,
                "next_stage": next_stage,
            }
        )
        saved = self.save(paused, event=("waiting_for_review", message or f"Chờ reviewer tại {checkpoint}"))
        self.emit(
            state.investigation_id,
            "checkpoint",
            f"Checkpoint {checkpoint}",
            {"checkpoint": str(checkpoint), "next_stage": next_stage, "version": saved.version},
        )
        return saved

    def resume(self, state: InvestigationState, *, next_stage: str | None = None) -> InvestigationState:
        """Đánh thức state đang chờ reviewer (không reset bộ đếm ngân sách)."""
        resumed = state.model_copy(
            update={
                "run_status": RunStatus.RUNNING,
                "checkpoint": None,
                "next_stage": next_stage if next_stage is not None else state.next_stage,
            }
        )
        return self.save(resumed, event=("resumed", "Tiếp tục chạy sau checkpoint review"))


class InProcessRunner:
    """Runner trong tiến trình API; một cuộc điều tra tại một thời điểm."""

    def __init__(self, store: MvpStore, executor: Executor | None = None, gateway: LLMGateway | None = None):
        self.store = store
        self.gateway = gateway or LLMGateway()
        self._executor = executor
        self._lock = threading.Lock()
        self._current: str | None = None
        self._cancelled_ids: set[str] = set()

    def is_cancelled(self, investigation_id: str) -> bool:
        return investigation_id in self._cancelled_ids

    def cancel(self, investigation_id: str, *, actor: str = "system", actor_role: str | None = None) -> InvestigationState:
        """Hủy cuộc điều tra: giải phóng runner nếu đang chạy, chuyển trạng thái sang CANCELLED.

        ``actor`` là **mã người** bấm hủy (AUTH-03/B1.7 mục 3) — trước đây thao tác của người dùng
        bị ghi nhật ký thành ``system``, nên không truy được ai đã hủy.
        """
        state = self.store.get_state(investigation_id)
        if state.run_status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            raise invalid_state(
                f"Cuộc điều tra đã ở trạng thái {state.run_status}, không thể hủy.",
                {"investigation_id": investigation_id, "run_status": str(state.run_status)},
            )
        self._cancelled_ids.add(investigation_id)
        cancelled_state = state.model_copy(update={"run_status": RunStatus.CANCELLED})
        saved = self.store.save_state(
            cancelled_state,
            event=("cancelled", "Người dùng đã hủy cuộc điều tra."),
            actor=actor,
            actor_role=actor_role,
        )
        return saved

    def register_resume(self, investigation_id: str, token: str | None) -> bool:
        """Ghi nhận yêu cầu chạy tiếp; ``False`` nghĩa là double-click đã xử lý.

        RV-06: khoá chống lặp nằm trong kho, không nằm trong RAM — sống sót qua khởi động lại
        tiến trình và dùng chung cho mọi tiến trình.
        """
        if token is None:
            return True
        return self.store.register_resume_request(investigation_id, token)

    def forget_resume(self, investigation_id: str, token: str | None) -> None:
        """Bỏ ghi nhận khi lần chạy tiếp không thực sự bắt đầu (lỗi/không chiếm được khoá)."""
        if token is None:
            return
        self.store.forget_resume_request(investigation_id, token)

    # ------------------------------------------------------------------ khóa

    @property
    def current(self) -> str | None:
        return self._current

    @property
    def is_busy(self) -> bool:
        return self._current is not None

    def acquire(self, investigation_id: str) -> None:
        if not self._lock.acquire(blocking=False):
            raise runner_busy(self._current)
        self._current = investigation_id

    def release(self) -> None:
        self._current = None
        self._lock.release()

    # ------------------------------------------------------------------ chạy

    @property
    def executor(self) -> Executor:
        if self._executor is None:
            from src.agents.graph import run_investigation

            return run_investigation
        return self._executor

    def context(self) -> RunContext:
        context = RunContext(store=self.store, gateway=self.gateway, runner=self)
        from src.config import get_settings

        settings = get_settings()
        if settings.mvp_source_mode == "live":
            from src.services.sources import build_adapters

            context.source_factory = lambda claim: build_adapters(
                snapshot_root=settings.mvp_snapshot_root,
                drug=claim.drug_ingredient,
                event=claim.event_term,
                max_documents=settings.mvp_source_max_documents,
                pubmed_mode=settings.mvp_pubmed_mode,
                pubmed_corpus_root=settings.mvp_pubmed_corpus_root,
            )
        elif settings.mvp_source_mode == "warehouse":
            # Truy hồi bằng chứng từ kho ELT + chỉ mục RAG thay vì gọi mạng.
            from src.services.sources.warehouse import build_warehouse_adapters
            from src.services.warehouse.db import get_warehouse_engine

            engine = get_warehouse_engine(settings.elt_database_url)
            context.source_factory = lambda claim: build_warehouse_adapters(
                engine=engine,
                settings=settings,
                drug=claim.drug_ingredient,
                event=claim.event_term,
                max_documents=settings.mvp_source_max_documents,
            )
        return context

    def run(self, investigation_id: str, *, resume: bool = False) -> InvestigationState:
        """Chạy đồng bộ tới khi dừng (hoàn tất hoặc chờ reviewer)."""
        self.acquire(investigation_id)
        try:
            state = self.store.get_state(investigation_id)
            if not resume and state.run_status not in (
                RunStatus.QUEUED,
                RunStatus.INTERRUPTED,
                RunStatus.WAITING_FOR_REVIEW,
            ):
                raise invalid_state(
                    f"Không thể chạy cuộc điều tra ở trạng thái {state.run_status}.",
                    {"investigation_id": investigation_id, "run_status": str(state.run_status)},
                )
            # ``resume`` giữ ``next_stage`` (điểm vào của graph) và giữ ``stop_reason`` gần nhất
            # (để hồ sơ ghi lại vì sao lượt chạy trước dừng), nhưng xoá checkpoint cũ để lần
            # dừng kế tiếp ghi nhận đúng checkpoint mới.
            update: dict[str, Any] = {"run_status": RunStatus.RUNNING, "checkpoint": None}
            if not resume:
                update["next_stage"] = None
                update["stop_reason"] = None
            state = self.store.save_state(
                state.model_copy(update=update), event=("running", "Agent bắt đầu chạy.")
            )
            result = self.executor(state, self.context())
            if result.run_status is RunStatus.RUNNING:
                result = self.store.save_state(
                    result.model_copy(update={"run_status": RunStatus.COMPLETED}),
                    event=("completed", "Agent kết thúc mà không còn bước chờ."),
                )
            return result
        except InvestigationCancelledError:
            state = self.store.get_state(investigation_id)
            if state.run_status is not RunStatus.CANCELLED:
                state = self.store.save_state(
                    state.model_copy(update={"run_status": RunStatus.CANCELLED}),
                    event=("cancelled", "Cuộc điều tra đã dừng lại do người dùng hủy."),
                )
            return state
        except Exception as exc:
            # Cancel can commit between RunContext's check and its versioned save.
            # That stale save must not turn the already-cancelled run into failed.
            if isinstance(exc, MvpError) and exc.code is ErrorCode.VERSION_CONFLICT:
                state = self.store.get_state(investigation_id)
                if state.run_status is RunStatus.CANCELLED:
                    return state
            self._mark_failed(investigation_id, exc)
            raise
        finally:
            self._cancelled_ids.discard(investigation_id)
            self.release()

    def start_background(self, investigation_id: str, *, resume: bool = False) -> None:
        """Chạy nền trong một thread riêng (dùng cho API 202 Accepted)."""
        thread = threading.Thread(
            target=self._run_guarded,
            args=(investigation_id, resume),
            name=f"mvp-runner-{investigation_id}",
            daemon=True,
        )
        thread.start()

    def _run_guarded(self, investigation_id: str, resume: bool) -> None:
        try:
            self.run(investigation_id, resume=resume)
        except InvestigationCancelledError:
            pass
        except MvpError as exc:
            if exc.code == ErrorCode.RUNNER_BUSY:
                # Không chiếm được khoá vì cuộc khác đang chạy: giữ trạng thái "queued" và ghi
                # sự kiện để client biết phải gọi /continue khi runner rảnh (không im lặng).
                self.store.append_event(
                    investigation_id,
                    "queued",
                    "Runner đang bận một cuộc điều tra khác; gọi /continue khi runner rảnh.",
                )
        except Exception:  # pragma: no cover - thread nền đã ghi trạng thái failed
            pass

    def _mark_failed(self, investigation_id: str, exc: Exception) -> None:
        if isinstance(exc, InvestigationCancelledError):
            return
        try:
            state = self.store.get_state(investigation_id)
        except Exception:  # pragma: no cover - không đọc được state
            return
        if state.run_status is RunStatus.FAILED:
            return
        self.store.save_state(
            state.model_copy(update={"run_status": RunStatus.FAILED}),
            event=("failed", f"Lỗi khi chạy: {exc}"),
        )

    # ------------------------------------------------------------------ phục hồi

    def recover_interrupted(self) -> list[str]:
        """Gọi lúc khởi động: run đang dở → ``interrupted`` (giữ counters/checkpoint)."""
        return self.store.mark_running_as_interrupted()


# --------------------------------------------------------------------------------------
# Singleton dùng chung cho API
# --------------------------------------------------------------------------------------

_runner: InProcessRunner | None = None


def configure_runner(store: MvpStore, executor: Executor | None = None, gateway: LLMGateway | None = None) -> InProcessRunner:
    global _runner
    _runner = InProcessRunner(store, executor=executor, gateway=gateway)
    _runner.recover_interrupted()
    return _runner


def get_runner() -> InProcessRunner:
    if _runner is None:  # pragma: no cover - API luôn cấu hình trước
        raise RuntimeError("Runner chưa được cấu hình (gọi configure_runner trước).")
    return _runner
