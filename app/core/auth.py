from fastapi.security import OAuth2AuthorizationCodeBearer
from app.core.config import settings

# OAuth2 Authorization Code + PKCE via Auth0, with OIDC scopes
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://{settings.auth0_domain}/authorize",
    tokenUrl=f"https://{settings.auth0_domain}/oauth/token",
    scopes={
        "openid": "Authenticate using OpenID Connect",
        "email": "Access to your email address",
        "profile": "Access to your basic profile information",
    },
)
