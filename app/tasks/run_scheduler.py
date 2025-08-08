import asyncio
import logging
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.tasks.badge_job import assign_due_badges
from app.tasks.motivation_job import generate_and_store_daily_text

log = logging.getLogger("scheduler")
logging.basicConfig(level=logging.INFO)


def make_scheduler() -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone=settings.timezone)

    def _listener(event):
        if event.exception:
            log.exception("Job %s failed", event.job_id, exc_info=event.exception)
        else:
            log.info("Job %s succeeded", event.job_id)

    s.add_listener(_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    s.add_job(
        generate_and_store_daily_text,
        trigger=IntervalTrigger(hours=8),
        id="motivation_interval_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        jitter=60,
    )
    s.add_job(
        assign_due_badges,
        trigger=IntervalTrigger(hours=24),
        id="badge_assign_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        jitter=60,
    )
    return s


async def main():
    scheduler = make_scheduler()
    scheduler.start()
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
