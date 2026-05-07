"""
SPASHT AI — Emergency Dispatch Backend
FastAPI + Groq (Llama 3.3-70b) AI Agent
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import json
import uuid
import traceback
from dotenv import load_dotenv
load_dotenv()
import os

groq_key = os.getenv("GROQ_API_KEY")

from models import (
    ChatRequest, ChatResponse, AnalyzeRequest, AnalyzeResponse,
    CallLog, CallLogEntry, CallEndRequest, IntentResult
)
from ai_agent import SPASHTAgent
from database import Database

# ── App startup/shutdown ──────────────────────────────────────────────────────

db = Database()
agent = SPASHTAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init()
    yield
    await db.close()

app = FastAPI(
    title="SPASHT AI — Emergency Dispatch API",
    description="AI-powered emergency dispatch system for 1092 helpline",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "online", "service": "SPASHT AI", "time": datetime.utcnow().isoformat()}

# ── AI Chat endpoint (streaming) ──────────────────────────────────────────────

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Stream the AI agent's response token-by-token.
    The AI speaks TO the person in distress — empathetic, calm, action-oriented.
    """
    async def generate():
        try:
            async for chunk in agent.stream_response(
                session_id=req.session_id,
                caller_message=req.message,
                location=req.location,
                history=req.history,
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Non-streaming chat — full AI response in one shot.
    Also returns intent analysis alongside the response.
    """
    try:
        response_text, intent = await agent.full_response(
            session_id=req.session_id,
            caller_message=req.message,
            location=req.location,
            history=req.history,
        )
        return ChatResponse(
            session_id=req.session_id,
            ai_message=response_text,
            intent=intent,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ── Intent analysis (standalone) ──────────────────────────────────────────────

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """
    Classify caller intent, urgency, and recommended dispatch decision.
    Can be called independently of the chat flow.
    """
    try:
        result = await agent.analyze_intent(req.text, req.history)
        return AnalyzeResponse(
            intent=result.intent,
            confidence=result.confidence,
            urgency=result.urgency,
            decision=result.decision,
            reasoning=result.reasoning,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Call log CRUD ─────────────────────────────────────────────────────────────

@app.get("/calls", response_model=CallLog)
async def get_calls(limit: int = 50):
    """Fetch recent call log entries."""
    entries = await db.get_calls(limit=limit)
    return CallLog(entries=entries, total=len(entries))


@app.post("/calls/end", response_model=CallLogEntry)
async def end_call(req: CallEndRequest):
    """Log a completed call with its final intent + decision."""
    entry = CallLogEntry(
        id=str(uuid.uuid4()),
        session_id=req.session_id,
        time=datetime.utcnow().strftime("%H:%M"),
        duration=req.duration,
        intent=req.intent,
        confidence=req.confidence,
        decision=req.decision,
        location=req.location,
        created_at=datetime.utcnow().isoformat(),
    )
    await db.save_call(entry)
    return entry


@app.get("/calls/{session_id}")
async def get_call(session_id: str):
    """Fetch a single call record by session ID."""
    entry = await db.get_call(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Call not found")
    return entry


@app.delete("/calls/{session_id}")
async def delete_call(session_id: str):
    await db.delete_call(session_id)
    return {"deleted": session_id}

# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/stats")
async def get_stats():
    """Aggregate stats for the dashboard stat cards."""
    calls = await db.get_calls(limit=1000)
    total = len(calls)
    return {
        "total":     total,
        "escalated": sum(1 for c in calls if c.decision == "ESCALATE"),
        "confirmed": sum(1 for c in calls if c.decision == "CONFIRM"),
        "proceeded": sum(1 for c in calls if c.decision == "PROCEED"),
    }
