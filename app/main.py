from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.api.v1.routers import auth, preference, motivation
from app.core.config import settings
from app.tasks.motivation_job import generate_and_store_daily_text


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        openapi_url=f"{settings.api_v1_str}/openapi.json",
        docs_url=f"{settings.api_v1_str}/docs",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backends_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix=f"{settings.api_v1_str}/auth", tags=["auth"])
    app.include_router(
        preference.router,
        prefix=f"{settings.api_v1_str}/preference",
        tags=["preference"],
    )
    app.include_router(
        motivation.router,
        prefix=f"{settings.api_v1_str}/motivation",
        tags=["motivation"],
    )

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
            minutes=0,
            id="motivation_interval_job",
            replace_existing=True,
        )
        scheduler.start()
        print("Scheduled 'motivation_interval_job' every 8 hours")

    return app


app = create_app()
