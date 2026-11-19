"""Proceso de worker independiente del request HTTP."""

from __future__ import annotations

import threading

from backend.config.settings import settings
from backend.infrastructure.persistence.platform_repository import PlatformRepository
from backend.workers.runner import worker_loop


def main() -> None:
    stop = threading.Event()
    store = PlatformRepository(settings.platform_db_path)
    worker_loop(store, stop)


if __name__ == "__main__":
    main()
