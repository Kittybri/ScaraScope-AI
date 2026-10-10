"""Downloadable PDF and XLSX. POST avoids putting research inputs in query URLs."""
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from .dependencies import get_settings,require_api_key
from ..core.config import Settings
from ..core.models import ResearchRequest
from ..services.agent import research_company
from ..data.sec import SECError
from ..reports.pdf import export_pdf
from ..reports.excel import export_excel
from ..observability.metrics import record

router=APIRouter(prefix="/api/reports",dependencies=[Depends(require_api_key)])

async def _prepare(request,settings):
    if request.privacy=="local_only" and request.provider=="cloud":
        raise HTTPException(status_code=400,detail="Cloud provider conflicts with local-only privacy.")
    try:
        return await research_company(request,settings)
    except SECError as exc:
        raise HTTPException(status_code=503,detail=str(exc)) from exc

@router.post("/research.pdf")
async def pdf(request: ResearchRequest,settings: Settings=Depends(get_settings)):
    report=await _prepare(request,settings)
    record("pdf_export_completed")
    return StreamingResponse(BytesIO(export_pdf(report)),media_type="application/pdf",
                             headers={"Content-Disposition":f'attachment; filename="scarascope-{request.ticker}.pdf"'})

@router.post("/research.xlsx")
async def xlsx(request: ResearchRequest,settings: Settings=Depends(get_settings)):
    report=await _prepare(request,settings)
    record("xlsx_export_completed")
    return StreamingResponse(BytesIO(export_excel(report)),media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition":f'attachment; filename="scarascope-{request.ticker}.xlsx"'})
