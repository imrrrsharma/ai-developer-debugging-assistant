from pydantic import BaseModel, Field, UUID4
from typing import Optional, List
from datetime import datetime


class QuickFix(BaseModel):
    label: str
    action: str
    command: Optional[str] = None


class AnalysisRequest(BaseModel):
    log_content: str = Field(..., min_length=10, description="Raw log text to analyze")
    hint: Optional[str] = Field(None, description="Optional hint about the system (e.g., 'Spring Boot 3.x')")


class AnalysisResponse(BaseModel):
    session_id: str
    log_type: str
    error_type: str
    root_cause: str
    explanation: str
    fix_suggestions: List[str]
    severity: str                       # LOW | MEDIUM | HIGH | CRITICAL
    confidence: float                   # 0.0–1.0
    possible_causes: List[str]
    quick_fixes: List[QuickFix]
    highlighted_lines: List[int]        # 0-indexed line numbers with errors
    service_name: Optional[str]
    error_message: Optional[str]
    processing_time_ms: int
    model_used: str


class HistoryItem(BaseModel):
    session_id: str
    created_at: datetime
    log_type: Optional[str]
    error_type: Optional[str]
    root_cause: Optional[str]
    severity: Optional[str]
    confidence: Optional[float]
    source_filename: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
    page: int
    page_size: int


class HistoryDetailResponse(AnalysisResponse):
    created_at: datetime
    raw_log: str
