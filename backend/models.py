from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from backend.database import Base


class DebugSession(Base):
    __tablename__ = "debug_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Input
    raw_log = Column(Text, nullable=False)
    log_type = Column(String(50), nullable=True)    # java_spring, nodejs, python, generic
    source_filename = Column(String(255), nullable=True)

    # Extracted fields
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    service_name = Column(String(255), nullable=True)
    timestamp_in_log = Column(String(100), nullable=True)

    # AI Analysis output
    error_type = Column(String(255), nullable=True)
    root_cause = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    fix_suggestions = Column(JSON, nullable=True)       # list[str]
    severity = Column(String(20), nullable=True)        # LOW/MEDIUM/HIGH/CRITICAL
    confidence = Column(Float, nullable=True)           # 0.0–1.0
    possible_causes = Column(JSON, nullable=True)       # list[str]
    quick_fixes = Column(JSON, nullable=True)           # list[{label, action}]

    # Meta
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
