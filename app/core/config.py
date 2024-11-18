from pydantic import Field
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    DB_USER: str = Field(default="postgres", env="POSTGRESQL_USER")
    DB_PASSWORD: str = Field(default="Lymann-2", env="POSTGRESQL_PASSWORD")
    DB_NAME: str = Field(default="fastapi", env="POSTGRESQL_DB")
    DB_HOST: str = Field(default="localhost", env="POSTGRESQL_SERVER")
    DB_PORT: str = Field(default="5432", env="POSTGRESQL_PORT")

    JWT_SECRET: str = Field(default="supersecretkey", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="JWT_TOKEN_EXPIRE_MINUTES")

    SECRET_KEY: str = Field(default="8d5f01d7a83a4c8abf0e3cb7...3c08a3f6f0e5d3d62c12345", env="SECRET_KEY")
    EMAIL_HOST: str = Field(default="smtp.gmail.com", env="EMAIL_HOST")
    EMAIL_PORT: str = Field(default="587", env="EMAIL_PORT")
    EMAIL_SENDER: str = Field(default="lymannphy9@gmail.com", env="EMAIL_SENDER")
    EMAIL_PASSWORD: str = Field(default="dqon ivdr jnbn ilvz", env="EMAIL_PASSWORD")
    EMAIL_USE_TLS: bool = Field(default=True, env="EMAIL_USE_TLS")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")


    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
