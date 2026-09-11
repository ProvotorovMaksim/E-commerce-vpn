from pydantic_settings import BaseSettings
from os import getenv
import json

class Settings(BaseSettings):
    TELEGRAM_TOKEN: str = getenv("TOKEN", "your_token")
    GIGACHAT_CREDENTIALS: str = getenv("GIGACHAT_CREDENTIALS", "")
    DATABASE_URL: str = getenv("DATABASE_URL", "")
    DATABASE_DRIVER: str = getenv("DATABASE_DRIVER", "")
    POSTGRES_USER: str = getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = getenv("POSTGRES_DB", "")
    NO_CREDENTIALS_PATHS: dict = json.loads(getenv("NO_CREDENTIALS_PATHS", "{}"))
    JWT_SECRET_KEY: str = getenv("JWT_SECRET_KEY", "")
    ALGORITHM: str = getenv("ALGORITHM", "")
    VPN_SERVICE_URL: str = getenv("VPN_SERVICE_URL", "")
    AUTH_SERVICE_URL: str = getenv("AUTH_SERVICE_URL", "")
    BILLING_SERVICE_URL: str = getenv("BILLING_SERVICE_URL", "")

    class Config:
        env_file = ".env"

settings = Settings()
 