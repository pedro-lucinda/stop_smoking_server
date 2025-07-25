from fastapi.openapi.utils import get_openapi
from typing import Any
from app.core.config import settings


def custom_openapi(app) -> Any:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    # OAuth2 security scheme
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["oauth2"] = {
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
    # Apply security globally
    schema["security"] = [{"oauth2": []}]
    # Remove legacy token parameters
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
