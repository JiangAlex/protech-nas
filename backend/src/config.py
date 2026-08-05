"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(Path(__file__).parent.parent / ".env.example")


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-to-random-secret")
    ADMIN_USER: str = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    JWT_ALGORITHM: str = "HS256"

    # OTA Update Settings
    OTA_SERVER_URL: str = os.getenv("OTA_SERVER_URL", "http://localhost:8060")
    OTA_DEVICE_ID: int = int(os.getenv("OTA_DEVICE_ID", "1"))
    OTA_DEPLOY_MODE: str = os.getenv("OTA_DEPLOY_MODE", "systemd")  # "systemd" or "docker"
    OTA_APP_DIR: str = os.getenv("OTA_APP_DIR", "/opt/protech-nas")
    OTA_WEB_DIR: str = os.getenv("OTA_WEB_DIR", "/var/www/protech-nas")


settings = Settings()
