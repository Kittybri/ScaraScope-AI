"""Lightweight optional local connectivity probe; never sends research content."""
import httpx
from ..core.config import Settings

async def provider_status(settings: Settings) -> dict:
    local = "disabled"
    if settings.ollama_enabled:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                response=await client.get(f"{settings.ollama_base_url}/api/tags")
                local="reachable" if response.status_code==200 else "unhealthy"
        except httpx.HTTPError:
            local="unavailable"
    return {"ollama":local,"groq":"configured (not probed)" if settings.groq_api_key else "not configured",
            "note":"Local probe checks connectivity, not whether model generation succeeds. Groq is not queried to avoid API usage."}
