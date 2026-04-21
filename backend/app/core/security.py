import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from app.core.config import settings
from fastapi import Response

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def set_auth_cookie(response: Response, token: str):
    """Sets the HttpOnly access token cookie."""
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

def set_csrf_cookie(response: Response, token: str):
    """
    Sets the CSRF token cookie. 
    IMPORTANT: httponly=False so frontend JS can read it for the Double-Submit pattern.
    """
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # Necessary for frontend to read and send back in header
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

def remove_auth_cookies(response: Response):
    """Wipes both access token and CSRF token cookies."""
    for key in ["access_token", "csrf_token"]:
        response.delete_cookie(
            key=key,
            httponly=True if key == "access_token" else False,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/"
        )

def generate_csrf_token() -> str:
    """Generate a highly secure cryptographically random token."""
    return secrets.token_urlsafe(32)
