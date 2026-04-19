"""
CRUD operations for DebugSession history.
"""
import uuid
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import DebugSession


async def save_session(db: AsyncSession, data: Dict[str, Any]) -> DebugSession:
    session = DebugSession(
        id=uuid.UUID(data["session_id"]),
        raw_log=data.get("_raw_log", ""),
        log_type=data.get("log_type"),
        source_filename=data.get("_source_filename"),
        error_message=data.get("error_message"),
        stack_trace=data.get("_stack_trace"),
        service_name=data.get("service_name"),
        timestamp_in_log=data.get("_timestamp_in_log"),
        error_type=data.get("error_type"),
        root_cause=data.get("root_cause"),
        explanation=data.get("explanation"),
        fix_suggestions=data.get("fix_suggestions"),
        severity=data.get("severity"),
        confidence=data.get("confidence"),
        possible_causes=data.get("possible_causes"),
        quick_fixes=[qf.model_dump() for qf in data.get("quick_fixes", [])],
        tokens_used=data.get("_tokens_used"),
        processing_time_ms=data.get("processing_time_ms"),
        model_used=data.get("model_used"),
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_history(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[DebugSession], int]:
    offset = (page - 1) * page_size

    count_q = select(func.count()).select_from(DebugSession)
    total = (await db.execute(count_q)).scalar_one()

    q = select(DebugSession).order_by(desc(DebugSession.created_at)).offset(offset).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return list(rows), total


async def get_session(db: AsyncSession, session_id: str) -> Optional[DebugSession]:
    try:
        uid = uuid.UUID(session_id)
    except ValueError:
        return None
    q = select(DebugSession).where(DebugSession.id == uid)
    return (await db.execute(q)).scalar_one_or_none()
