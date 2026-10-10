"""Simple deterministic routing and provider fallback, with privacy enforcement."""
from ..core.config import Settings
from ..core.models import LLMResult, ResearchRequest
from .providers.base import LLMProvider, ProviderError
from .providers.groq import GroqProvider
from .providers.ollama import OllamaProvider

COMPLEX_WORDS = {"compare", "valuation", "forecast", "scenario", "model", "sensitivity", "multi-step", "acquisition", "discounted", "regression"}


def is_complex(question: str, years: int) -> bool:
    question = question.lower()
    return years >= 4 or len(question) > 350 or any(word in question for word in COMPLEX_WORDS)


class ModelRouter:
    def __init__(self, settings: Settings, local: LLMProvider | None = None, cloud: LLMProvider | None = None):
        self.settings = settings
        self.local = local or OllamaProvider(settings)
        self.cloud = cloud or GroqProvider(settings)

    async def explain(self, request: ResearchRequest, system: str, prompt: str, fallback_text: str) -> LLMResult:
        if request.provider == "none":
            return LLMResult(provider="deterministic", model="none", text=fallback_text, note="AI explanation disabled by request.")
        if request.privacy == "local_only" and request.provider == "cloud":
            raise ValueError("Cloud inference cannot be selected with local-only privacy.")
        if request.privacy == "local_only":
            preferred = ["local"]
        elif request.provider == "local":
            preferred = ["local", "cloud"]
        elif request.provider == "cloud":
            preferred = ["cloud", "local"]
        else:
            preferred = ["cloud", "local"] if is_complex(request.question, request.years) else ["local", "cloud"]
        attempts = []
        first_choice = preferred[0]
        for name in preferred:
            if name == "local" and not self.settings.ollama_enabled:
                continue
            if name == "cloud" and not self.settings.groq_api_key:
                continue
            try:
                provider = self.local if name == "local" else self.cloud
                text = await provider.generate(system, prompt)
                return LLMResult(provider="ollama" if name == "local" else "groq", model=self.settings.ollama_model if name == "local" else self.settings.groq_model, text=text, fallback_used=name != first_choice, note="; ".join(attempts) or None)
            except ProviderError as exc:
                attempts.append(f"{name}: {exc}")
        reason = "; ".join(attempts) or "No usable LLM provider is configured."
        if request.privacy == "local_only":
            reason += " Cloud fallback was disabled by privacy policy."
        return LLMResult(provider="deterministic", model="none", text=fallback_text, fallback_used=bool(attempts), note=reason)
