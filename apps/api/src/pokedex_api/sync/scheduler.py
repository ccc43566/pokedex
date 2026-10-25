from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore[import-untyped]

from pokedex_api.sync.cli import run_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def sync_job() -> None:
    try:
        result = asyncio.run(run_sync(force=False, download_media=True))
        logger.info("Scheduled sync result: %s", result)
    except Exception:
        logger.exception("Scheduled PokeAPI sync failed")


def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        sync_job,
        trigger="interval",
        weeks=1,
        id="pokeapi-weekly-sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(UTC),
    )
    logger.info("Starting weekly PokeAPI sync scheduler")
    scheduler.start()


if __name__ == "__main__":
    main()
