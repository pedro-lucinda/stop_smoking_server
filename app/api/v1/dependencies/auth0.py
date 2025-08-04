import os
from typing import Dict

import httpx
import requests
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt
from sqlalchemy.orm import Session

from app.api.v1.dependencies.db import get_db_session
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

_jwks_cache = None


def get_jwks() -> Dict:
    global _jwks_cache
    if _jwks_cache is None:
        resp = requests.get(f"https://{auth0_domain}/.well-known/jwks.json")
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


def fetch_userinfo(token: str) -> Dict:
    """
    Fetch full user profile from Auth0 UserInfo endpoint.
    """
    resp = requests.get(
        f"https://{auth0_domain}/userinfo", headers={"Authorization": f"Bearer {token}"}
    )
    if not resp.ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to fetch user profile",
        )
    return resp.json()


def get_current_user(
    token: str = Security(oauth2_scheme),
    db: Session = Depends(get_db_session),
) -> User:
    """
    1) Verify & decode the Auth0 JWT
    2) Fetch user profile via /userinfo to get email, name, etc.
    3) Look up or lazy-provision the User by auth0_id
    4) Return the SQLAlchemy User instance
    """
    # 1) Verify access token
    _ = verify_jwt(token)

    # 2) Fetch full user profile
    profile = fetch_userinfo(token)
    auth0_sub = profile.get("sub")
    email = profile.get("email")
    name = profile.get("name")

    if not auth0_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="UserInfo missing 'sub'"
        )

    # 3) Lookup or create user
    user = db.query(User).filter(User.auth0_id == auth0_sub).first()
    if not user:
        user = User(
            auth0_id=auth0_sub,
            email=email or "",
            name=name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

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
    r = httpx.patch(url, json=payload, headers=headers)
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
