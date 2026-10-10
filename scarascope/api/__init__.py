"""Public ASGI import: uvicorn scarascope.api:app."""
from .app import app
from .dependencies import get_settings

__all__ = ["app", "get_settings"]
