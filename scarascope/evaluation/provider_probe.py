"""Explicit opt-in, bounded live provider latency/error smoke test.

Never reports simulated results as actual Groq/Ollama metrics; never saves
prompts, outputs, API keys, token estimates or fictional dollar costs.
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Literal

from ..ai.providers.base import ProviderError, LLMProvider
from ..ai.providers.ollama import OllamaProvider
from ..ai.providers.groq import GroqProvider
from ..core.config import Settings
from .runner import save_report

_TEST_SYSTEM = "Answer elementary arithmetic with a single number."
_TEST_QUESTION = "Calculate 2 + 2. Respond with the number only."


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered=sorted(values)
    return round(ordered[max(0,ceil(percentile*len(ordered))-1)],3)


async def measure_provider(provider: LLMProvider, *, name: str, model: str,
                           iterations: int = 3) -> dict:
    if not 1<=iterations<=5 or name not in {"ollama", "groq"}:
        raise ValueError("Probe requires 1–5 runs and an explicit provider.")
    cases=[]
    for index in range(iterations):
        start=perf_counter()
        try:
            response=await provider.generate(_TEST_SYSTEM,_TEST_QUESTION)
            passed=bool(response.strip())
            # Don't retain provider-generated content: it can be sensitive or untrusted.
            outcome="success" if passed else "empty"
        except (ProviderError, TimeoutError, ValueError):
            outcome="failed"
        duration=round((perf_counter()-start)*1000,3)
        cases.append({"iteration":index+1,"status":outcome,"latency_ms":duration})
    times=[row["latency_ms"] for row in cases if row["status"]=="success"]
    return {"benchmark":"live_provider_smoke_v1","captured_at":datetime.now(timezone.utc).isoformat(),
            "provider":name,"model":model,"invocations":iterations,
            "successful":len(times),"p50_success_ms":_percentile(times,0.5),
            "p95_success_ms":_percentile(times,0.95),"cases":cases,
            "cost_usd":None,"tokens_used":None,"answer_accuracy":None,
            "limitations":["Measures live request outcomes and wall-clock latency only.",
                           "Trivial arithmetic prompt is NOT an independently validated financial QA set.",
                           "No token usage or billed provider cost available from current adapter contract.",
                           "Local and cloud probes are opt-in and may incur provider charges."]}


def main() -> None:
    parser=argparse.ArgumentParser(description="Live inference smoke test; requires explicit opt-in")
    parser.add_argument("--provider",choices=["local","cloud"],required=True)
    parser.add_argument("--confirm-live",action="store_true",help="Allow 1-5 real inference requests")
    parser.add_argument("--allow-cloud",action="store_true",help="Separate consent for paid cloud requests")
    parser.add_argument("--iterations",type=int,default=3)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if not args.confirm_live:
        parser.error("Real model calls require --confirm-live; no calls were made.")
    if not 1<=args.iterations<=5:
        parser.error("Choose 1–5 iterations maximum.")
    settings=Settings()
    if args.provider=="cloud":
        if not args.allow_cloud or not settings.groq_api_key:
            parser.error("Cloud probe requires --allow-cloud and GROQ_API_KEY.")
        provider=GroqProvider(settings)
        model=settings.groq_model
        label="groq"
    else:
        if not settings.ollama_enabled:
            parser.error("Enable OLLAMA_ENABLED and configure the local model first.")
        provider=OllamaProvider(settings)
        model=settings.ollama_model
        label="ollama"
    report=asyncio.run(measure_provider(provider,name=label,model=model,iterations=args.iterations))
    if args.output:
        save_report(report,args.output)
    print(json.dumps(report,indent=2))
    if report["successful"]!=report["invocations"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
