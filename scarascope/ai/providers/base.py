"""Small provider contract shared by Ollama, Groq and test doubles."""
from typing import Protocol


class ProviderError(Exception):
    """Expected provider error; never expose credentials or raw private prompts."""


class LLMProvider(Protocol):
    async def generate(self, system: str, prompt: str) -> str: ...
