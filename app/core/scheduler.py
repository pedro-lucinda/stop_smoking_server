from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.tasks.motivation_job import generate_and_store_daily_text
from app.core.config import settings


def init_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    def _job_listener(event):
        if event.exception:
            print(f"Job {event.job_id} failed", exc_info=event.exception)
        else:
            print(f"Job {event.job_id} succeeded at {datetime.now()}")

    scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    @app.on_event("startup")
    def start_scheduler():
        scheduler.add_job(
            generate_and_store_daily_text,
            trigger="interval",
            hours=8,
            id="motivation_interval_job",
            replace_existing=True,
        )
        scheduler.start()
        print("Scheduled 'motivation_interval_job' every 8 hours")
