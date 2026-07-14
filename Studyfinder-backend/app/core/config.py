from decouple import config
from typing import List


class Settings:
    # App
    APP_NAME: str = config("APP_NAME", default="Study Group Finder")
    DEBUG: bool = config("DEBUG", default=False, cast=bool)
    SECRET_KEY: str = config("SECRET_KEY")
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = config("DATABASE_URL")

    # JWT
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = config("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default=15, cast=int)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = config("JWT_REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int)

    # Email
    MAIL_USERNAME: str = config("MAIL_USERNAME", default="")
    MAIL_PASSWORD: str = config("MAIL_PASSWORD", default="")
    MAIL_FROM: str = config("MAIL_FROM", default="")
    MAIL_PORT: int = config("MAIL_PORT", default=587, cast=int)
    MAIL_SERVER: str = config("MAIL_SERVER", default="smtp.gmail.com")
    MAIL_STARTTLS: bool = config("MAIL_STARTTLS", default=True, cast=bool)
    MAIL_SSL_TLS: bool = config("MAIL_SSL_TLS", default=False, cast=bool)

    # Redis
    REDIS_HOST: str = config("REDIS_HOST", default="localhost")
    REDIS_PORT: int = config("REDIS_PORT", default=6379, cast=int)

    # Frontend
    FRONTEND_URL: str = config("FRONTEND_URL", default="http://localhost:3000")

    # CORS
    CORS_ORIGINS: List[str] = config(
        "CORS_ORIGINS",
        default="http://localhost:3000",
        cast=lambda v: [s.strip() for s in v.split(",")]
    )


settings = Settings()
