from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User as UserModel

# Use HTTP Bearer instead of OAuth2 password flow
bearer_scheme = HTTPBearer()


def get_db_session() -> Generator[Session, None, None]:
    """
    Provide a database session for a request.
    """
    yield from get_db()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> UserModel:
    """
    Validate the JWT and retrieve the current user.

    - Extracts the bearer token from the Authorization header.
    - Verifies token signature & expiration.
    - Extracts the 'sub' claim as the user ID.
    - Fetches the corresponding user from the database.
    - Raises 401 if token is invalid or user not found.
    """
    token = credentials.credentials  # raw JWT string

    # Decode & verify JWT
    try:
        payload = decode_access_token(token)
        # payload.get("sub") is typed as Any | None, but at runtime it's a str
        user_id: int = int(payload.get("sub"))  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Fetch user
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
