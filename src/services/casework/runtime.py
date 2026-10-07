"""Safe bridge between durable casework commands and the existing MVP runtime.

The bridge never manufactures a drug/event claim.  The legacy runner is only considered
for a scoped DI run after the casework readiness gate has confirmed an unambiguous scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import Settings
from src.services.runner import InProcessRunner
from src.services.sources import build_adapters
from src.services.store import MvpStore


@dataclass
class CaseworkRuntimeBridge:
    """Runtime dependencies created behind a small, injectable seam.

    Casework owns its command/outbox state in the warehouse.  ``MvpStore`` remains a
    separate SQLite checkpoint store and is not touched unless the command passed the
    workflow readiness gate.
    """

    settings: Settings
    mvp_store: MvpStore
    runner: InProcessRunner

    @classmethod
    def from_settings(cls, settings: Settings) -> CaseworkRuntimeBridge:
        from src.api.mvp_runtime import configure_mvp, get_mvp_runner

        store = configure_mvp(settings.casework_runtime_db_path)
        return cls(settings=settings, mvp_store=store, runner=get_mvp_runner())

    def can_start_scoped(self, readiness: dict[str, Any], assertions: list[dict[str, Any]]) -> bool:
        if not readiness.get("can_run_scoped_analysis"):
            return False
        confirmed = {item.get("field_key") for item in assertions if item.get("status") == "confirmed"}
        # The existing DI runner requires a real drug/event-shaped claim.  Do not select
        # an ambiguous candidate merely to satisfy it.
        return bool(confirmed & {"drug", "event_outcome"})

    def source_adapters(self, assertions: list[dict[str, Any]]) -> dict[str, Any]:
        """Build configured adapters only for a confirmed search term.

        This is deliberately retrieval-only: callers persist SourceResult outcomes and
        leave clinical confirmation and review to the workflow service.
        """
        values = {
            str(item.get("field_key")): str(item.get("value"))
            for item in assertions
            if item.get("status") == "confirmed" and item.get("value")
        }
        drug = values.get("drug")
        event = values.get("event_outcome")
        if not drug and not event:
            return {}
        return build_adapters(
            snapshot_root=self.settings.mvp_snapshot_root,
            drug=drug or "",
            event=event or "",
            max_documents=self.settings.mvp_source_max_documents,
            pubmed_mode=self.settings.mvp_pubmed_mode,
            pubmed_corpus_root=self.settings.mvp_pubmed_corpus_root,
        )
