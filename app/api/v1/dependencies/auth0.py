from typing import Dict, List, Optional

import httpx
import requests
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.async_db_session import get_async_db
from app.core.config import settings
from app.models.user import User

# Auth0 configuration
auth0_domain = settings.auth0_domain
api_audience = settings.auth0_api_audience
algorithms = ["RS256"]
client_id = settings.auth0_mgmt_client_id
client_secret = settings.auth0_mgmt_client_secret

# OAuth2 scheme for Swagger UI & header parsing
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://{auth0_domain}/authorize",
    tokenUrl=f"https://{auth0_domain}/oauth/token",
    scopes={},
)

_jwks_cache: Optional[Dict] = None


def get_jwks() -> Dict:
    global _jwks_cache
    if _jwks_cache is None:
        resp = requests.get(
            f"https://{auth0_domain}/.well-known/jwks.json", timeout=5.0
        )
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def verify_jwt(token: str) -> Dict:
    jwks = get_jwks()
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header."
        )

    rsa_key = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == header.get("kid"):
            rsa_key = {
                "kty": key.get("kty"),
                "kid": key.get("kid"),
                "use": key.get("use"),
                "n": key.get("n"),
                "e": key.get("e"),
            }
            break

    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not find appropriate key.",
        )

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=algorithms,
            audience=api_audience,
            issuer=f"https://{auth0_domain}/",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired."
        )
    except jwt.JWTClaimsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate token."
        )


def get_token_payload(token: str = Security(oauth2_scheme)) -> Dict:
    """Dependency that verifies the token and returns its decoded payload."""
    return verify_jwt(token)


async def get_current_user(
    db: AsyncSession = Depends(get_async_db),
    token_data: Dict = Depends(get_token_payload),
    raw_token: str = Security(oauth2_scheme),
) -> User:
    auth0_sub = token_data.get("sub")
    if not auth0_sub:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim.")

    # Try to find existing user by auth0_id
    result = await db.execute(select(User).where(User.auth0_id == auth0_sub))
    user = result.scalar_one_or_none()

    if user is None:
        # Pull claims
        email = token_data.get("email")
        given_name = token_data.get("given_name")
        family_name = token_data.get("family_name")
        full_name = (
            token_data.get("name")
            or " ".join(n for n in (given_name, family_name) if n)
            or None
        )
        picture = token_data.get("picture")  # will map to User.img

        # If missing essentials, try /userinfo
        if not (email and full_name):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(
                        f"https://{auth0_domain}/userinfo",
                        headers={"Authorization": f"Bearer {raw_token}"},
                    )
                if r.status_code == 200:
                    info = r.json()
                    email = email or info.get("email")
                    given_name = given_name or info.get("given_name")
                    family_name = family_name or info.get("family_name")
                    full_name = full_name or info.get("name")
                    picture = picture or info.get("picture")
            except Exception:
                pass  # don’t fail login if userinfo fetch fails

        if not email:
            # Your model requires email (nullable=False); fail cleanly if we still don't have it
            raise HTTPException(status_code=400, detail="User email is required")

        # Create user with correct field names
        user = User(
            auth0_id=auth0_sub,
            email=email,
            name=full_name,
            surname=family_name,
            img=picture,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


def get_m2m_token() -> str:
    resp = httpx.post(
        f"https://{auth0_domain}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": f"https://{auth0_domain}/api/v2/",
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def update_user_email(auth0_id: str, new_email: str):
    token = get_m2m_token()
    url = f"https://{auth0_domain}/api/v2/users/{auth0_id}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "email": new_email,
        "email_verified": False,  # force re-verify
        "verify_email": True,  # trigger the confirmation email
    }
    r = httpx.patch(url, json=payload, headers=headers, timeout=10.0)
    r.raise_for_status()
    return r.json()


def can_update_email(auth0_id: str) -> bool:
    token = get_m2m_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Only fetch the identities field
    url = f"https://{auth0_domain}/api/v2/users/{auth0_id}?fields=identities"
    r = httpx.get(url, headers=headers, timeout=5.0)
    r.raise_for_status()
    identities = r.json().get("identities", [])
    # “auth0” provider == native database user
    return any(idf.get("provider") == "auth0" for idf in identities)


def require_permission(permission: str):
    """
    Router-level dependency: checks the permission in the token.
    Usage: dependencies=[Depends(require_permission("manage:badges"))]
    """

    async def checker(token_data: Dict = Depends(get_token_payload)):
        # Auth0 can place permissions either in a 'permissions' array, or in 'scope' (space-delimited)
        perms: List[str] = token_data.get("permissions") or []
        if not perms:
            scope = token_data.get("scope", "")
            perms = scope.split() if scope else []

        if permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        # No return needed; this is just a guard.

    return checker
