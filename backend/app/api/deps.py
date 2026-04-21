from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import secrets

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

async def get_token_from_cookie(request: Request) -> str:
    """Extract and validate the bearer token from the httponly cookie."""
    authorization = request.cookies.get("access_token")
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session format")
    
    return token

async def get_current_user(
    request: Request,
    token: str = Depends(get_token_from_cookie),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates the session token AND enforces CSRF protection for mutating requests.
    Supports standard 'Double Submit Cookie' pattern.
    """
    # 1. Strict CSRF & Origin Protection for mutating methods
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        # Origin/Referer Validation (Defense-in-depth)
        origin = request.headers.get("Origin") or request.headers.get("Referer")
        allowed_origins = [str(o) for o in settings.BACKEND_CORS_ORIGINS]
        
        if origin:
            # Check if origin starts with any allowed origin
            if not any(origin.startswith(allowed) for allowed in allowed_origins):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Unauthorized origin/referer"
                )

        # Double-Submit Cookie CSRF Validation
        header_csrf = request.headers.get("X-CSRF-Token")
        cookie_csrf = request.cookies.get("csrf_token")
        
        if not header_csrf:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Missing CSRF header (X-CSRF-Token)"
            )
        if not cookie_csrf:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Missing CSRF cookie"
            )
            
        if not secrets.compare_digest(header_csrf, cookie_csrf):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="CSRF validation failed: token mismatch"
            )
        
    # 2. JWT Verification
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid session: subject missing"
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Session expired or invalid"
        )

    # 3. User Resolution
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is deactivated")
        
    return user
