from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import urllib.parse
import secrets
import structlog

from app.api.deps import get_db, get_current_user
from app.services.auth import AuthService
from app.core.config import settings
from app.core.security import (
    create_access_token, 
    set_auth_cookie, 
    set_csrf_cookie,
    remove_auth_cookies,
    generate_csrf_token,
)
from app.schemas.user import UserResponse
from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/login/google")
async def login_google(request: Request):
    """
    Initiates the OAuth2 flow with Google.
    Generates a state parameter to prevent CSRF during OAuth.
    """
    state_token = secrets.token_urlsafe(32)
    abs_redirect_uri = str(request.url_for("callback_google"))
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": abs_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state_token,
        "access_type": "online",
        "prompt": "select_account"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    response = JSONResponse({"authorization_url": url})
    # Use hardened settings for the state cookie
    response.set_cookie(
        key="oauth_state",
        value=state_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=300
    )
    return response

@router.get("/callback/google")
async def callback_google(
    request: Request, 
    code: str = None, 
    state: str = None, 
    error: str = None, 
    db: AsyncSession = Depends(get_db)
):
    """Handles callback from Google Identity."""
    if error:
        # Redact the raw error in public response, log type only
        logger.error("oauth_callback_failed", error_type=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth authentication failed.")
        
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state")

    saved_state = request.cookies.get("oauth_state")
    if not saved_state or saved_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
        
    abs_redirect_uri = str(request.url_for("callback_google"))
    service = AuthService(db)
    
    try:
        user = await service.handle_google_login_callback(code, abs_redirect_uri)
    except Exception as e:
        logger.error("google_callback_logic_error", error_class=type(e).__name__)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User authentication failed.")
        
    access_token = create_access_token(subject=user.id)
    csrf_token = generate_csrf_token()
    
    # Redirect back to the frontend shell upon success
    response = RedirectResponse(url=settings.FRONTEND_URL)
    set_auth_cookie(response, access_token)
    set_csrf_cookie(response, csrf_token)
    
    # Explicitly clear state with correct path
    response.delete_cookie(
        "oauth_state", 
        httponly=True, 
        secure=settings.COOKIE_SECURE, 
        samesite=settings.COOKIE_SAMESITE,
        path="/"
    )
    return response

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(user: User = Depends(get_current_user)):
    """Returns the authenticated user details."""
    return user

@router.get("/csrf")
async def get_csrf(request: Request):
    """
    Ensures a CSRF token is set. 
    Useful for initializing the CSRF cookie on first load/redirect.
    """
    current_csrf = request.cookies.get("csrf_token")
    response = JSONResponse({"detail": "CSRF token initialized"})
    
    if not current_csrf:
        new_token = generate_csrf_token()
        set_csrf_cookie(response, new_token)
    
    return response

@router.post("/logout")
async def logout():
    """Wipes all auth and CSRF cookies."""
    response = JSONResponse({"detail": "Logged out successfully"})
    remove_auth_cookies(response)
    return response
