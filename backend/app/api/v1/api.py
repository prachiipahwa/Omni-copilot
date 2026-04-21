from fastapi import APIRouter
from app.core.security import generate_csrf_token
from fastapi.responses import JSONResponse
from app.api.v1.endpoints import auth, chats, integrations, retrieval, indexing, search, orchestration

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(indexing.router, prefix="/indexing", tags=["indexing"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(orchestration.router, prefix="/chat", tags=["chat"])

@api_router.get("/health")
def health_check():
    return {"status": "ok"}

@api_router.get("/csrf-token")
def get_csrf_token():
    """Endpoint for the frontend to request a CSRF token.
    Sets the token in an HttpOnly=False (or strict) cookie, and returns it.
    The frontend reads the cookie and sends it in the X-CSRF-Token header.
    Wait, double submit means we set a cookie (HttpOnly=False or True) and the frontend reads it or we return it in JSON and frontend sets header.
    Let's return it un-httponly as well as header.
    Actually, standard double-submit: backend sets 'csrf_token' cookie (HttpOnly=False or True). If True, frontend can't read it. The frontend gets it from the JSON payload.
    Frontend passes JSON payload token as 'X-CSRF-Token' header. 
    Backend verifies X-CSRF-Token == Request.cookies.get('csrf_token')
    """
    token = generate_csrf_token()
    response = JSONResponse({"detail": "CSRF token generated", "csrf_token": token})
    # CSRF cookie MUST be HttpOnly=True for security. Frontend gets token from JSON payload, stores in memory or sends header.
    from app.core.config import settings
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=True,  # Prevent JS access to the actual token cookie
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/"
    )
    return response
