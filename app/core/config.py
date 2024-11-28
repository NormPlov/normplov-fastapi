import os

from pydantic import Field
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    BASE_UPLOAD_FOLDER: str = Field(default="uploads", env="BASE_UPLOAD_FOLDER")

    @property
    def LEARNING_STYLE_UPLOAD_FOLDER(self) -> str:
        return os.path.join(self.BASE_UPLOAD_FOLDER, "learning_style")

    DB_USER: str = Field(default="postgres", env="POSTGRESQL_USER")
    DB_PASSWORD: str = Field(default="Lymann-2", env="POSTGRESQL_PASSWORD")
    DB_NAME: str = Field(default="fastapi", env="POSTGRESQL_DB")
    DB_HOST: str = Field(default="localhost", env="POSTGRESQL_SERVER")
    DB_PORT: str = Field(default="5432", env="POSTGRESQL_PORT")

    JWT_SECRET: str = Field(default="supersecretkey", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="JWT_TOKEN_EXPIRE_MINUTES")
    SECRET_KEY: str = Field(default="8d5f01d7a83a4c8abf0e3cb7...3c08a3f6f0e5d3d62c12345", env="SECRET_KEY")

    # Email Configuration
    EMAIL_HOST: str = Field(default="smtp.gmail.com", env="EMAIL_HOST")
    EMAIL_PORT: str = Field(default="587", env="EMAIL_PORT")
    EMAIL_SENDER: str = Field(default="lymannphy9@gmail.com", env="EMAIL_SENDER")
    EMAIL_PASSWORD: str = Field(default="dqon ivdr jnbn ilvz", env="EMAIL_PASSWORD")
    EMAIL_USE_TLS: bool = Field(default=True, env="EMAIL_USE_TLS")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Google Configuration
    GOOGLE_CLIENT_ID: str = Field(..., env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/auth/google/callback", env="GOOGLE_REDIRECT_URI")

    # Google API Key
    GOOGLE_GENERATIVE_AI_KEY: str = Field(default="AIzaSyBs8q5cZDyFDPVqiN5JJ8loS_Qt2SiHsRk", env="GOOGLE_GENERATIVE_AI_KEY")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
