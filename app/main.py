from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import health, motivation, preference, user, diary, craving
from app.core.config import settings
from app.core.openapi import custom_openapi
from app.core.scheduler import init_scheduler


def create_app() -> FastAPI:
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

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backends_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
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
    app.include_router(
        health.router,
        prefix=f"{settings.api_v1_str}/health",
        tags=["health"],
    )
    app.include_router(
        diary.router,
        prefix=f"{settings.api_v1_str}/diary",
        tags=["diary"],
    )
    app.include_router(
        craving.router,
        prefix=f"{settings.api_v1_str}/craving",
        tags=["craving"],
    )

    # Scheduler
    init_scheduler(app)

    # Custom OpenAPI
    app.openapi = lambda: custom_openapi(app)

    return app


# Instantiate
app = create_app()
