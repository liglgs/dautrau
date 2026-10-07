"""Run the durable casework command processor.

Usage: ``python -m src.casework_worker``.  It is deliberately separate from the
API process so only one deployment role owns a runtime SQLite namespace at a time.
"""

from __future__ import annotations

import logging
import time

from src.config import get_settings
from src.services.casework.processor import CaseworkCommandProcessor
from src.services.casework.runtime import CaseworkRuntimeBridge
from src.services.warehouse.db import get_warehouse_engine


def main() -> None:
    settings = get_settings()
    processor = CaseworkCommandProcessor(
        get_warehouse_engine(settings.elt_database_url),
        CaseworkRuntimeBridge.from_settings(settings),
        lease_seconds=settings.casework_worker_lease_seconds,
    )
    logging.info("casework worker started")
    while True:
        processed = processor.process_once()
        if processed is None:
            time.sleep(1)


if __name__ == "__main__":
    main()
