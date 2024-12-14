from typing import List

from pydantic import Field, validator
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # Environment Configuration
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # File Upload Configuration
    ALLOWED_EXTENSIONS: List[str] = Field(..., env="ALLOWED_EXTENSIONS")
    MAX_FILE_SIZE: int = Field(default=5 * 1024 * 1024, env="MAX_FILE_SIZE")
    BASE_UPLOAD_FOLDER: str = Field(default="uploads", env="BASE_UPLOAD_FOLDER")

    # Database Configuration
    DB_USER: str = Field(default="postgres", env="POSTGRESQL_USER")
    DB_PASSWORD: str = Field(default="password", env="POSTGRESQL_PASSWORD")
    DB_NAME: str = Field(default="postgres", env="POSTGRESQL_DB")
    DB_HOST: str = Field(default="136.228.158.126", env="POSTGRESQL_SERVER")
    DB_PORT: str = Field(default="3299", env="POSTGRESQL_PORT")

    # JWT Configuration
    JWT_SECRET: str = Field(default="-vv7YfCkPifps-Vg7sc-dOXHzImbV3sN8NJN-vfTiBuDCmzTtCVHMHGNhQJ5FsvIbk3Q8hyKClFRW_DnZ7uswQ", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=3, env="JWT_TOKEN_EXPIRE_MINUTES")
    SECRET_KEY: str = Field(default="8d5f01d7a83a4c8abf0e3cb7...3c08a3f6f0e5d3d62c12345", env="SECRET_KEY")

    # Email Configuration
    EMAIL_HOST: str = Field(default="smtp.gmail.com", env="EMAIL_HOST")
    EMAIL_PORT: int = Field(default=587, env="EMAIL_PORT")
    EMAIL_SENDER: str = Field(default="lymannphy9@gmail.com", env="EMAIL_SENDER")
    EMAIL_PASSWORD: str = Field(default="dqon ivdr jnbn ilvz", env="EMAIL_PASSWORD")
    EMAIL_USE_TLS: bool = Field(default=True, env="EMAIL_USE_TLS")

    # Debug and Environment Settings
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Google Configuration
    GOOGLE_CLIENT_ID: str = Field(..., env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/auth/google/callback", env="GOOGLE_REDIRECT_URI")

    # Google Generative AI Key
    GOOGLE_GENERATIVE_AI_KEY: str = Field(default="AIzaSyBs8q5cZDyFDPVqiN5JJ8loS_Qt2SiHsRk", env="GOOGLE_GENERATIVE_AI_KEY")

    # In the Settings class

    TELEGRAM_BOT_TOKEN: str = Field(default="7747910734:AAHKkDzr54-oMuRs7SuEvN13MxmUBKB6QxM", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field(default="1299615474", env="TELEGRAM_CHAT_ID")

    # Validator for ALLOWED_EXTENSIONS
    @validator("ALLOWED_EXTENSIONS", pre=True)
    def parse_allowed_extensions(cls, value):
        if isinstance(value, str):
            return [ext.strip() for ext in value.split(",") if ext.strip()]
        return value

    # Database URL Configuration
    @property
    def database_url(self) -> str:
        db_host = "136.228.158.126" if self.ENVIRONMENT == "development" else self.DB_HOST
        return f"postgresql+asyncpg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{db_host}:{self.DB_PORT}/{self.DB_NAME}"


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
