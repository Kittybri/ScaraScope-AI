"""FastAPI dependency overrides and API-key protection."""
import secrets
from fastapi import Depends, Header, HTTPException
from ..core.config import Settings


def get_settings() -> Settings:
    return Settings()


def require_api_key(x_api_key: str | None = Header(default=None), settings: Settings = Depends(get_settings)) -> None:
    if settings.require_auth and not settings.app_api_key:
        raise HTTPException(status_code=503, detail="Private API authentication is required but SCARASCOPE_API_KEY is not configured.")
    if settings.app_api_key and not secrets.compare_digest(x_api_key or "", settings.app_api_key):
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")
