"""Thin HTTP boundary for SEC passage retrieval and document Q&A."""
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import get_settings, require_api_key
from ..core.config import Settings
from ..data.sec.client import SECError
from ..services.document_qa import DocumentQuestion, DocumentAnswer, answer_document_question

router = APIRouter(prefix="/api/documents", tags=["SEC Document Q&A"],
                   dependencies=[Depends(require_api_key)])


@router.post("/ask", response_model=DocumentAnswer)
async def ask_document(request: DocumentQuestion, settings: Settings = Depends(get_settings)):
    try:
        return await answer_document_question(request, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SECError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
