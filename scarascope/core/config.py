"""Runtime settings. External credentials are always loaded from environment."""
from dataclasses import dataclass, field
import os

from dotenv import load_dotenv

load_dotenv()


def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
        return max(1.0, min(120.0, value))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    sec_user_agent: str = field(default_factory=lambda: os.getenv("SEC_USER_AGENT", "").strip())
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))
    groq_base_url: str = field(default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"))
    ollama_enabled: bool = field(default_factory=lambda: os.getenv("OLLAMA_ENABLED", "false").lower() in ("1", "true", "yes"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    local_timeout: float = field(default_factory=lambda: _float_env("LOCAL_TIMEOUT_SECONDS", 25.0))
    cloud_timeout: float = field(default_factory=lambda: _float_env("CLOUD_TIMEOUT_SECONDS", 35.0))
    history_db_path: str = field(default_factory=lambda: os.getenv("HISTORY_DB_PATH", "./data/history.sqlite3"))
    embedding_model_path: str = field(default_factory=lambda: os.getenv("SCARASCOPE_EMBEDDING_MODEL_PATH", "").strip())
    app_api_key: str = field(default_factory=lambda: os.getenv("SCARASCOPE_API_KEY", "").strip())
    require_auth: bool = field(default_factory=lambda: os.getenv("SCARASCOPE_REQUIRE_AUTH", "false").lower() in ("1", "true", "yes"))
    request_limit_per_minute: int = field(default_factory=lambda: min(240, max(10, int(os.getenv("SCARASCOPE_REQUESTS_PER_MINUTE", "60")))))

    @property
    def sec_ready(self) -> bool:
        return bool(self.sec_user_agent and "example.com" not in self.sec_user_agent.lower())
