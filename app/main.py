from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2AuthorizationCodeBearer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.api.v1.routers import preference, motivation, user
from app.core.config import settings
from app.tasks.motivation_job import generate_and_store_daily_text

# OAuth2 Authorization Code + PKCE via Auth0, requesting email and profile scopes
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://{settings.auth0_domain}/authorize",
    tokenUrl=f"https://{settings.auth0_domain}/oauth/token",
    scopes={
        "openid": "Authenticate using OpenID Connect",
        "email": "Access to your email address",
        "profile": "Access to your basic profile information",
    },
)


def create_app() -> FastAPI:
    # Create FastAPI with Swagger UI OAuth2 init
    app = FastAPI(
        title=settings.app_name,
        openapi_url=f"{settings.api_v1_str}/openapi.json",
        docs_url=f"{settings.api_v1_str}/docs",
        swagger_ui_init_oauth={
            "clientId": settings.auth0_client_id,
            "usePkceWithAuthorizationCodeGrant": True,
            "redirectUrl": f"{settings.api_v1_str}/docs/oauth2-redirect",
            "additionalQueryStringParams": {
                "audience": settings.auth0_api_audience,
                "scope": "openid profile email",
            },
            "scopeSeparator": " ",
        },
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backends_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers (security enforced via Security dependency inside routers)
    app.include_router(
        user.router,
        prefix=f"{settings.api_v1_str}/user",
        tags=["user"],
    )
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

    # Background scheduler
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

    # Customize OpenAPI to include OAuth2 scopes and strip legacy query params
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version="1.0.0", routes=app.routes)

        # Define OAuth2 security scheme with scopes
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "oauth2"
        ] = {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"https://{settings.auth0_domain}/authorize",
                    "tokenUrl": f"https://{settings.auth0_domain}/oauth/token",
                    "refreshUrl": None,
                    "scopes": {
                        "openid": "Authenticate using OpenID Connect",
                        "email": "Access to your email address",
                        "profile": "Access to your basic profile information",
                    },
                }
            },
        }
        # Apply security to all operations
        schema["security"] = [{"oauth2": []}]

        # Remove any leftover 'token' query parameters
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                params = operation.get("parameters", [])
                operation["parameters"] = [
                    p
                    for p in params
                    if not (p.get("name") == "token" and p.get("in") == "query")
                ]

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
    return app


# Instantiate app
app = create_app()
