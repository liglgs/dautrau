from __future__ import annotations

from src.services.casework.models import CaseworkCommand, CaseworkRun
from src.services.casework.processor import CaseworkCommandProcessor
from src.services.casework.store import CaseWorkStore
from src.services.warehouse.db import get_warehouse_engine, session_scope


def test_processor_completes_persisted_intake_command_and_is_replay_safe(tmp_path):
    engine = get_warehouse_engine(f"sqlite:///{tmp_path / 'processor.db'}")
    store = CaseWorkStore(engine)
    receipt = store.create_intake(
        kind="di",
        raw_text="Cần tư vấn thuốc?",
        actor={"id": "investigator", "role": "investigator"},
        idempotency_key="intake-command",
    )
    processor = CaseworkCommandProcessor(engine, bridge=None, lease_seconds=10)
    processed = processor.process_once()
    assert processed == {"command_id": receipt["operation_id"], "state": "completed"}
    assert processor.process_once() is None
    with session_scope(engine) as session:
        command = session.get(CaseworkCommand, receipt["operation_id"])
        assert command.state == "completed"
        assert command.cursor_json["outcome"] == "no_automatic_confirmation"


def test_processor_preserves_missing_source_semantics_without_inventing_claims(tmp_path):
    engine = get_warehouse_engine(f"sqlite:///{tmp_path / 'processor-scope.db'}")
    store = CaseWorkStore(engine)
    receipt = store.create_intake(
        kind="di",
        raw_text="Cần tư vấn?",
        actor={"id": "investigator", "role": "investigator"},
        idempotency_key="scoped-intake",
    )
    # Finish the automatic extraction command before starting the explicit analysis.
    processor = CaseworkCommandProcessor(engine, bridge=None)
    processor.process_once()
    run = store.create_casework_run(
        work_item_id=receipt["work_item_id"],
        purpose="preliminary_retrieval",
        actor={"id": "investigator", "role": "investigator"},
        idempotency_key="preliminary-run",
    )
    outcome = processor.process_once()
    assert outcome == {"command_id": run["operation_id"], "state": "completed"}
    with session_scope(engine) as session:
        row = session.get(CaseworkRun, run["run_id"])
        assert row.state == "completed"
        assert row.source_results_json == [
            {
                "source": "runtime",
                "outcome": "skipped",
                "coverage": "not_requested",
                "retryable": False,
                "detail": "No live retrieval was performed by this worker.",
            }
        ]
        assert row.error_json is None
