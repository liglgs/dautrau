"""Lease-based durable processor for casework commands.

Commands are intentionally small.  A restart can claim a lease-expired command again;
publishing is fenced by its generation so an old worker cannot overwrite a newer result.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.engine import Engine

from src.services.casework.models import CaseworkCommand, CaseworkRun, CaseworkWorkflow, InputRevision, WorkItem
from src.services.casework.runtime import CaseworkRuntimeBridge
from src.services.warehouse.db import session_scope
from src.services.warehouse.models import now


class CaseworkCommandProcessor:
    def __init__(self, engine: Engine, bridge: CaseworkRuntimeBridge | None = None, *, lease_seconds: int = 60):
        self.engine = engine
        self.bridge = bridge
        self.lease_seconds = lease_seconds

    def process_once(self) -> dict[str, Any] | None:
        claimed = self._claim()
        if claimed is None:
            return None
        try:
            return self._execute(claimed)
        except Exception as exc:  # commands must retain a retryable failure, not disappear
            self._finish(claimed, state="failed", error={"kind": type(exc).__name__, "message": str(exc)[:500]})
            return {"command_id": claimed["command_id"], "state": "failed"}

    def _claim(self) -> dict[str, Any] | None:
        with session_scope(self.engine) as session:
            stamp = now()
            row = (
                session.execute(
                    select(CaseworkCommand)
                    .where(
                        or_(
                            CaseworkCommand.state == "queued",
                            (CaseworkCommand.state == "running") & (CaseworkCommand.lease_until < stamp),
                        )
                    )
                    .order_by(CaseworkCommand.created_at, CaseworkCommand.command_id)
                )
                .scalars()
                .first()
            )
            if row is None:
                return None
            generation = row.generation + 1
            result = session.execute(
                update(CaseworkCommand)
                .where(CaseworkCommand.command_id == row.command_id, CaseworkCommand.generation == row.generation)
                .values(
                    state="running",
                    generation=generation,
                    lease_until=stamp + timedelta(seconds=self.lease_seconds),
                    error_json=None,
                    updated_at=stamp,
                )
            )
            if result.rowcount != 1:
                return None
            return {
                "command_id": row.command_id,
                "work_item_id": row.work_item_id,
                "run_id": row.run_id,
                "command_type": row.command_type,
                "payload": dict(row.payload_json or {}),
                "generation": generation,
            }

    def _execute(self, command: dict[str, Any]) -> dict[str, Any]:
        kind = command["command_type"]
        if kind == "extract_fields":
            # Intake was already committed.  We deliberately do not infer or confirm facts
            # from free text in this safe offline processor.
            self._finish(
                command, state="completed", cursor={"stage": "extraction", "outcome": "no_automatic_confirmation"}
            )
            return {"command_id": command["command_id"], "state": "completed"}
        if kind in {"preliminary_retrieval", "scoped_analysis"}:
            return self._run_retrieval(command)
        self._finish(command, state="failed", error={"kind": "unsupported_command", "command_type": kind})
        return {"command_id": command["command_id"], "state": "failed"}

    def _run_retrieval(self, command: dict[str, Any]) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            workflow = session.get(CaseworkWorkflow, command["work_item_id"])
            if workflow is None:
                raise RuntimeError("workflow missing for command")
            revision = session.execute(
                select(InputRevision).where(
                    InputRevision.work_item_id == command["work_item_id"],
                    InputRevision.revision == workflow.input_revision,
                )
            ).scalar_one()
            run = session.get(CaseworkRun, command["run_id"])
            if run is None:
                raise RuntimeError("run missing for command")
            assertions = list(revision.assertions_json or [])
            readiness = dict(workflow.readiness_json or {})
            if command["command_type"] == "scoped_analysis" and (
                self.bridge is None or not self.bridge.can_start_scoped(readiness, assertions)
            ):
                run.state, run.error_json, run.updated_at = (
                    "failed",
                    {"kind": "readiness", "message": "Scoped analysis requires confirmed, unambiguous DI scope."},
                    now(),
                )
                result = {"command_id": command["command_id"], "state": "failed"}
            else:
                # Do not perform live network calls from the durable worker by default.  The
                # configured source adapters are still used as the DI seam once an operator
                # enables a runtime bridge; absent adapters is explicit, never an empty result.
                adapters = self.bridge.source_adapters(assertions) if self.bridge else {}
                outcome = "not_requested" if not adapters else "partial"
                run.source_results_json = [
                    {"source": name, "outcome": "skipped", "coverage": "not_requested", "retryable": False}
                    for name in adapters
                ] or [
                    {
                        "source": "runtime",
                        "outcome": "skipped",
                        "coverage": outcome,
                        "retryable": False,
                        "detail": "No live retrieval was performed by this worker.",
                    }
                ]
                run.state, run.updated_at = "completed", now()
                work = session.get(WorkItem, command["work_item_id"])
                if work is not None:
                    work.run_status = "completed"
                result = {"command_id": command["command_id"], "state": "completed"}
        self._finish(command, state=result["state"], cursor={"stage": "retrieval", "result": result["state"]})
        return result

    def _finish(
        self,
        command: dict[str, Any],
        *,
        state: str,
        cursor: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        with session_scope(self.engine) as session:
            result = session.execute(
                update(CaseworkCommand)
                .where(
                    CaseworkCommand.command_id == command["command_id"],
                    CaseworkCommand.generation == command["generation"],
                )
                .values(state=state, cursor_json=cursor, error_json=error, lease_until=None, updated_at=now())
            )
            # A stale worker must not publish over the current generation.
            if result.rowcount != 1:
                return
