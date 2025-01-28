import os
from typing import List

from pydantic import Field, validator
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # Frontend URL Configuration
    FRONTEND_URL: str = Field(default="https://normplov.istad.co", env="FRONTEND_URL")

    # Environment Configuration
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # File Upload Configuration
    ALLOWED_EXTENSIONS: List[str] = Field(..., env="ALLOWED_EXTENSIONS")
    MAX_FILE_SIZE: int = Field(default=5 * 1024 * 1024, env="MAX_FILE_SIZE")
    BASE_UPLOAD_FOLDER: str = Field(default="uploads", env="BASE_UPLOAD_FOLDER")

    # Database Configuration for Production
    DB_USER: str = Field(default="postgres", env="POSTGRESQL_USER")
    DB_PASSWORD: str = Field(default="password", env="POSTGRESQL_PASSWORD")
    DB_NAME: str = Field(default="postgres", env="POSTGRESQL_DB")
    DB_HOST: str = Field(default="202.178.125.77", env="POSTGRESQL_SERVER")
    DB_PORT: str = Field(default="3299", env="POSTGRESQL_PORT")

    # JWT Configuration
    JWT_SECRET: str = Field(default="-vv7YfCkPifps-Vg7sc-dOXHzImbV3sN8NJN-vfTiBuDCmzTtCVHMHGNhQJ5FsvIbk3Q8hyKClFRW_DnZ7uswQ", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=3, env="JWT_TOKEN_EXPIRE_MINUTES")
    SECRET_KEY: str = Field(default="8d5f01d7a83a4c8abf0e3cb7...3c08a3f6f0e5d3d62c12345", env="SECRET_KEY")

    # Email Configuration
    EMAIL_HOST: str = Field(default="smtp.gmail.com", env="EMAIL_HOST")
    EMAIL_PORT: int = Field(default=587, env="EMAIL_PORT")
    EMAIL_SENDER: str = Field(default="normplov.istad@gmail.com", env="EMAIL_SENDER")
    EMAIL_PASSWORD: str = Field(default="jmve hjoo lqix gaec", env="EMAIL_PASSWORD")
    EMAIL_USE_TLS: bool = Field(default=True, env="EMAIL_USE_TLS")

    # Debug and Environment Settings
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Login with Google
    GOOGLE_CLIENT_ID: str = Field(..., env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., env="GOOGLE_CLIENT_SECRET")

    # Login with Facebook
    FACEBOOK_CLIENT_ID: str = Field(..., env="FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: str = Field(..., env="FACEBOOK_CLIENT_SECRET")
    FACEBOOK_REDIRECT_URI: str = Field(default="https://normplov-api.shinoshike.studio/api/v1/auth/facebook/callback",
                                       env="FACEBOOK_REDIRECT_URI")

    # Google Generative AI Key
    GOOGLE_GENERATIVE_AI_KEYS: List[str] = Field(default=["AIzaSyBxll6Nb_N2PBgmz9NM5a8tVOXHD0nN8Ak"],
                                                 env="GOOGLE_GENERATIVE_AI_KEYS")

    @validator("GOOGLE_GENERATIVE_AI_KEYS", pre=True)
    def parse_google_ai_keys(cls, value):
        if isinstance(value, str):
            return [key.strip() for key in value.split(",") if key.strip()]
        if isinstance(value, list):
            return value
        raise ValueError("GOOGLE_GENERATIVE_AI_KEYS must be a comma-separated string or a list.")

    TELEGRAM_BOT_TOKEN: str = Field(default="7747910734:AAHKkDzr54-oMuRs7SuEvN13MxmUBKB6QxM", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field(default="1299615474", env="TELEGRAM_CHAT_ID")

    # Google Maps Configuration
    GOOGLE_MAPS_API_KEY: str = Field(..., env="GOOGLE_MAPS_API_KEY")

    # Validator for ALLOWED_EXTENSIONS
    @validator("ALLOWED_EXTENSIONS", pre=True)
    def parse_allowed_extensions(cls, value):
        if isinstance(value, str):
            return [ext.strip() for ext in value.split(",") if ext.strip()]
        return value

    # Database URL Configuration
    @property
    def database_url(self) -> str:
        db_host = "202.178.125.77" if self.ENVIRONMENT == "development" else self.DB_HOST
        return f"postgresql+asyncpg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{db_host}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
