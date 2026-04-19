import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import HistoryResponse, HistoryItem, HistoryDetailResponse, QuickFix
from backend.services import history_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    sessions, total = await history_service.get_history(db, page=page, page_size=page_size)
    items = [
        HistoryItem(
            session_id=str(s.id),
            created_at=s.created_at,
            log_type=s.log_type,
            error_type=s.error_type,
            root_cause=s.root_cause,
            severity=s.severity,
            confidence=s.confidence,
            source_filename=s.source_filename,
            error_message=s.error_message,
        )
        for s in sessions
    ]
    return HistoryResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/history/{session_id}", response_model=HistoryDetailResponse)
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> HistoryDetailResponse:
    s = await history_service.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    quick_fixes = [QuickFix(**qf) for qf in (s.quick_fixes or [])]

    return HistoryDetailResponse(
        session_id=str(s.id),
        created_at=s.created_at,
        raw_log=s.raw_log,
        log_type=s.log_type or "generic",
        error_type=s.error_type or "",
        root_cause=s.root_cause or "",
        explanation=s.explanation or "",
        fix_suggestions=s.fix_suggestions or [],
        severity=s.severity or "MEDIUM",
        confidence=s.confidence or 0.5,
        possible_causes=s.possible_causes or [],
        quick_fixes=quick_fixes,
        highlighted_lines=[],
        service_name=s.service_name,
        error_message=s.error_message,
        processing_time_ms=s.processing_time_ms or 0,
        model_used=s.model_used or "",
    )
