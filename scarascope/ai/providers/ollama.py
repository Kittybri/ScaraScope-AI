"""Ollama chat API adapter (usually a model running on the laptop)."""
import httpx
from ...core.config import Settings
from .base import ProviderError


class OllamaProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(self, system: str, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.settings.local_timeout) as client:
                response = await client.post(f"{self.settings.ollama_base_url}/api/chat", json={
                    "model": self.settings.ollama_model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                    "stream": False, "options": {"num_predict": 650},
                })
                response.raise_for_status()
                result = response.json().get("message", {}).get("content")
                if not isinstance(result, str) or not result.strip():
                    raise ProviderError("Ollama returned an empty answer.")
                return result.strip()
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Local model unavailable, timed out, or returned an invalid response.") from exc


