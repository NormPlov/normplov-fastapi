import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    DB_USER: str = os.getenv("POSTGRESQL_USER", "postgres")
    DB_PASSWORD: str = os.getenv("POSTGRESQL_PASSWORD", "Lymann-2")
    DB_NAME: str = os.getenv("POSTGRESQL_DB", "fastapi")
    DB_HOST: str = os.getenv("POSTGRESQL_SERVER", "localhost")
    DB_PORT: str = os.getenv("POSTGRESQL_PORT", "5432")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkey")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_TOKEN_EXPIRE_MINUTES", 60))

settings = Settings()
