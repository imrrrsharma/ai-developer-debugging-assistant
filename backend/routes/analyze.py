import uuid
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import AnalysisRequest, AnalysisResponse, QuickFix
from backend.services import ai_analyzer, history_service
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analysis"])

_MB = 1024 * 1024


@router.post("/analyze-log", response_model=AnalysisResponse)
async def analyze_log(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    session_id = str(uuid.uuid4())
    try:
        result = await ai_analyzer.analyze(
            raw_log=request.log_content,
            session_id=session_id,
            hint=request.hint or "",
        )
        await history_service.save_session(db, result)
        return _to_response(result)
    except Exception as exc:
        logger.exception("analyze_log failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload-log", response_model=AnalysisResponse)
async def upload_log(
    file: UploadFile = File(...),
    hint: Annotated[str, Form()] = "",
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    max_bytes = settings.MAX_LOG_SIZE_MB * _MB
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_LOG_SIZE_MB} MB limit.",
        )

    try:
        raw_log = content.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode file as UTF-8.")

    session_id = str(uuid.uuid4())
    try:
        result = await ai_analyzer.analyze(
            raw_log=raw_log,
            session_id=session_id,
            hint=hint,
            source_filename=file.filename,
        )
        await history_service.save_session(db, result)
        return _to_response(result)
    except Exception as exc:
        logger.exception("upload_log failed")
        raise HTTPException(status_code=500, detail=str(exc))


def _to_response(data: dict) -> AnalysisResponse:
    return AnalysisResponse(
        session_id=data["session_id"],
        log_type=data["log_type"],
        error_type=data["error_type"],
        root_cause=data["root_cause"],
        explanation=data["explanation"],
        fix_suggestions=data["fix_suggestions"],
        severity=data["severity"],
        confidence=data["confidence"],
        possible_causes=data["possible_causes"],
        quick_fixes=data["quick_fixes"],
        highlighted_lines=data["highlighted_lines"],
        service_name=data.get("service_name"),
        error_message=data.get("error_message"),
        processing_time_ms=data["processing_time_ms"],
        model_used=data["model_used"],
    )
