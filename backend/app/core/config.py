from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Omni Copilot"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    FRONTEND_URL: str = "http://localhost:3000"
    
    # DB
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "omnicopilot"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None

    @model_validator(mode="after")
    def assemble_db_connection(self) -> 'Settings':
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self.DATABASE_URL or ""

    # Auth & Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    
    # OAuth 2.0 Identity & Tools
    GOOGLE_CLIENT_ID: str = "placeholder_id"
    GOOGLE_CLIENT_SECRET: str = "placeholder_secret"
    
    # Token Encryption at Rest
    ENCRYPTION_KEY: str
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Retrieval & Indexing
    SYNC_DRIVE_MAX_RESULTS: int = 25
    SYNC_EMAIL_MAX_RESULTS: int = 20
    SYNC_CALENDAR_MAX_RESULTS: int = 20
    INGESTION_CONCURRENCY: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

settings = Settings()
