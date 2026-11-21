"""Proceso de worker independiente del request HTTP."""

from __future__ import annotations

import threading

from backend.api.app_factory import prepare_database
from backend.infrastructure.persistence.platform_repository import PlatformRepository
from backend.workers.runner import worker_loop


def main() -> None:
    prepare_database()
    stop = threading.Event()
    store = PlatformRepository()
    worker_loop(store, stop)


if __name__ == "__main__":
    main()
