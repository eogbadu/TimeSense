import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class TokenUser(BaseModel):
    uid: str
    email: str | None = None
    role: str = "user"
    email_verified: bool = False


def _verify_token(token: str) -> TokenUser:
    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=True)
        return TokenUser(
            uid=decoded["uid"],
            email=decoded.get("email"),
            role=decoded.get("role", "user"),
            email_verified=decoded.get("email_verified", False),
        )
    except firebase_auth.RevokedIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please sign in again.",
        ) from exc
    except firebase_auth.ExpiredIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
        ) from exc
    except firebase_auth.InvalidIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected auth error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        ) from exc


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _verify_token(credentials.credentials)


async def require_admin(
    user: Annotated[TokenUser, Depends(get_current_user)],
) -> TokenUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


# Type aliases for use in route signatures
CurrentUser = Annotated[TokenUser, Depends(get_current_user)]
AdminUser = Annotated[TokenUser, Depends(require_admin)]
