"""
Pydantic models for SPASHT AI API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ── Chat ─────────────────────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    role: Literal["caller", "ai", "system"]
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique call session ID")
    message: str = Field(..., min_length=1, description="Caller's message")
    location: Optional[str] = Field(None, description="Caller location if known")
    history: List[HistoryEntry] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "call-abc123",
                "message": "Someone is following me, I'm really scared",
                "location": "Sector 14, New Delhi",
                "history": []
            }
        }


class IntentResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    urgency: Literal["HIGH", "MEDIUM", "LOW"]
    decision: Literal["ESCALATE", "CONFIRM", "PROCEED"]
    reasoning: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    ai_message: str
    intent: Optional[IntentResult] = None
    timestamp: str


# ── Analyze ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    history: List[HistoryEntry] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "text": "There's a fire and I smell smoke everywhere",
                "history": []
            }
        }


class AnalyzeResponse(BaseModel):
    intent: str
    confidence: float
    urgency: str
    decision: str
    reasoning: Optional[str] = None


# ── Call Log ──────────────────────────────────────────────────────────────────

class CallLogEntry(BaseModel):
    id: str
    session_id: str
    time: str                      # HH:MM display string
    duration: str                  # e.g. "2m 14s"
    intent: str
    confidence: float
    decision: Literal["ESCALATE", "CONFIRM", "PROCEED"]
    location: Optional[str] = None
    created_at: str


class CallLog(BaseModel):
    entries: List[CallLogEntry]
    total: int


class CallEndRequest(BaseModel):
    session_id: str
    duration: str
    intent: str
    confidence: float
    decision: Literal["ESCALATE", "CONFIRM", "PROCEED"]
    location: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "call-abc123",
                "duration": "2m 14s",
                "intent": "Harassment / Stalking",
                "confidence": 0.94,
                "decision": "ESCALATE",
                "location": "Sector 14, New Delhi"
            }
        }
