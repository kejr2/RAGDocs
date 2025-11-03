from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # PostgreSQL Settings
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "ragdocs"
    POSTGRES_PASSWORD: str = "ragdocs_password"
    POSTGRES_DB: str = "ragdocs_db"
    
    # Qdrant Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    
    # Connection retry settings
    DB_RETRY_ATTEMPTS: int = 5
    DB_RETRY_DELAY: int = 2
    
    # Gemini AI Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

