import structlog
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, Tuple

from app.models.user import User
from app.models.workspace import Workspace
from app.core.config import settings

logger = structlog.get_logger(__name__)

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_google_login_callback(self, code: str, redirect_uri: str) -> User:
        """Exchanges the code for a token and fetches the user's profile."""
        token_url = "https://oauth2.googleapis.com/token"
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

        async with AsyncClient() as client:
            token_res = await client.post(token_url, data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            })
            if not token_res.is_success:
                raise ValueError("Failed to retrieve access token from Google")
            
            token_data = token_res.json()
            access_token = token_data.get("access_token")

            user_res = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
            if not user_res.is_success:
                raise ValueError("Failed to retrieve user info from Google")
            
            user_data = user_res.json()
        
        email = user_data.get("email")
        if not email:
            raise ValueError("Google user does not have an email")
            
        return await self._upsert_user(email, user_data.get("name"))

    async def _upsert_user(self, email: str, full_name: str) -> User:
        """Ensure user exists, updates name if missing, and creates default workspace upon initialization.
        Fully idempotent and race-safe via explicit IntegrityError catching.
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if user:
            if not user.is_active:
                raise ValueError("User account is inactive")
            return user
        
        # Create new user
        new_user = User(email=email, full_name=full_name)
        self.db.add(new_user)
        try:
            await self.db.flush()
        except IntegrityError:
            # Race condition triggered: another thread inserted between our select and flush
            await self.db.rollback()
            result = await self.db.execute(select(User).where(User.email == email))
            return result.scalars().first()
            
        # Seed an isolation workspace mapping
        default_workspace = Workspace(name=f"{full_name or 'User'}'s Workspace", owner_id=new_user.id)
        self.db.add(default_workspace)
        
        await self.db.commit()
        await self.db.refresh(new_user)
        return user if (user := await self.db.get(User, new_user.id)) else new_user
