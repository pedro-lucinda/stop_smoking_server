from datetime import datetime

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.tasks.badge_job import assign_due_badges
from app.tasks.motivation_job import generate_and_store_daily_text


def init_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    def _job_listener(event):
        if event.exception:
            print(f"Job {event.job_id} failed", event.exception)
        else:
            print(f"Job {event.job_id} succeeded at {datetime.utcnow()} UTC")

    scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    @app.on_event("startup")
    def start_scheduler():
        # Motivation text every 8 hours
        scheduler.add_job(
            generate_and_store_daily_text,
            trigger="interval",
            hours=1440,
            id="motivation_interval_job",
            replace_existing=True,
        )
        print("Scheduled 'motivation_interval_job' every 8 hours")

        # Badge assignment every 24 hours (1440 minutes)
        scheduler.add_job(
            assign_due_badges,
            trigger="interval",
            minutes=1440,
            id="badge_assign_job",
            replace_existing=True,
        )
        print("Scheduled 'badge_assign_job' every 1440 minutes")

        scheduler.start()
        print("Scheduler started")
