"""Groq cloud chat API adapter; no credentials stored in code."""
import httpx
from ...core.config import Settings
from .base import ProviderError


class GroqProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(self, system: str, prompt: str) -> str:
        if not self.settings.groq_api_key:
            raise ProviderError("Groq is not configured.")
        try:
            async with httpx.AsyncClient(timeout=self.settings.cloud_timeout) as client:
                response = await client.post(f"{self.settings.groq_base_url}/chat/completions", headers={
                    "Authorization": f"Bearer {self.settings.groq_api_key}",
                    "Content-Type": "application/json",
                }, json={
                    "model": self.settings.groq_model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                    "temperature": 0.1, "max_tokens": 650,
                })
                response.raise_for_status()
                result = response.json()["choices"][0]["message"]["content"]
                if not isinstance(result, str) or not result.strip():
                    raise ProviderError("Groq returned an empty answer.")
                return result.strip()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise ProviderError("Groq quota or rate limit reached.") from exc
            raise ProviderError(f"Groq returned HTTP {status}.") from exc
        except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Groq unavailable, timed out, or returned an invalid response.") from exc
