"""Independent routes for research agent, comparisons, DCF and diagnostics."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .dependencies import get_settings, require_api_key
from ..core.config import Settings
from ..core.models import ResearchRequest
from ..finance.valuation import DCFInput, DCFResult, calculate_dcf, dcf_sensitivity
from ..finance.comparisons import ComparisonResult
from ..services.agent import AgentReport, research_company
from ..services.comparison import compare_companies
from ..data.sec import SECError
from ..observability.metrics import record, snapshot
from ..evaluation.benchmark import run_benchmark
from ..ai.availability import provider_status

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])

class ComparisonRequest(BaseModel):
    left: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9.-]{0,11}$")
    right: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9.-]{0,11}$")
    years: int = Field(default=3,ge=2,le=5)

@router.post("/compare",response_model=ComparisonResult)
async def comparison(req: ComparisonRequest, settings: Settings = Depends(get_settings)):
    try:
        result = await compare_companies(req.left.upper(),req.right.upper(),settings,years=req.years)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    except SECError as exc:
        raise HTTPException(status_code=503,detail=str(exc)) from exc
    record("comparison_completed")
    return result

@router.post("/valuation/dcf")
async def valuation(spec: DCFInput):
    value=calculate_dcf(spec)
    record("dcf_completed")
    return {"result":value,"sensitivity":dcf_sensitivity(spec)}

@router.post("/agent/research",response_model=AgentReport)
async def agent_research(request: ResearchRequest,settings: Settings = Depends(get_settings)):
    if request.privacy=="local_only" and request.provider=="cloud":
        raise HTTPException(status_code=400,detail="Cloud provider conflicts with local-only privacy.")
    try:
        result=await research_company(request,settings)
    except SECError as exc:
        raise HTTPException(status_code=503,detail=str(exc)) from exc
    record("agent_research_completed",provider=result.research.llm.provider)
    return result

@router.get("/evaluation/deterministic")
async def evaluation():
    return run_benchmark()

@router.get("/diagnostics")
async def diagnostics():
    return snapshot()

@router.get("/providers/status")
async def providers_status(settings:Settings=Depends(get_settings)):
    return await provider_status(settings)
