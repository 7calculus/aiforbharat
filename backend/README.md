# SPASHT AI — Emergency Dispatch System
### 1092 Helpline · FastAPI Backend + Groq AI Agent

---

## Architecture

```
Frontend (React/Vite)  ←→  Backend (FastAPI)  ←→  Groq AI (Llama 3.3-70b)
                                   ↕
                            SQLite (call logs)
```

**Why Groq?**  Free API · Ultra-low latency (avg ~300ms) · Llama 3.3-70b is excellent at
empathetic conversation and structured JSON output — both needed here.

**Why FastAPI?**  Groq's Python SDK is first-class · async streaming built-in ·
auto-generates Swagger docs at `/docs` · Pydantic models give you type safety throughout.

---

## Quick Start

### 1. Get a free Groq API key
→ https://console.groq.com  (takes 30 seconds, no credit card)

### 2. Backend setup

```bash
cd spasht-backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env → paste your GROQ_API_KEY

# Run the server
uvicorn main:app --reload --port 8000
```

Server starts at http://localhost:8000  
Swagger UI at http://localhost:8000/docs

### 3. Frontend setup

```bash
cd aiforbharat-frontend

# (optional) set API URL if backend is not on localhost:8000
# create .env.local with: VITE_API_URL=http://your-server:8000

npm install
npm run dev
```

Frontend starts at http://localhost:5173

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/health` | Server health check |
| POST | `/chat` | Send caller message → get AI response + intent |
| POST | `/chat/stream` | Same but streams tokens (SSE) |
| POST | `/analyze` | Standalone intent classification |
| GET  | `/calls` | Fetch call log (last 50) |
| POST | `/calls/end` | Log a completed call |
| GET  | `/calls/{session_id}` | Fetch single call |
| GET  | `/stats` | Dashboard aggregate stats |

### Example: Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "call-001",
    "message": "Someone is following me, I am scared!",
    "location": "Sector 14, New Delhi",
    "history": []
  }'
```

Response:
```json
{
  "session_id": "call-001",
  "ai_message": "I hear you and I am with you right now. You are safe to talk to me. Can you tell me — are you still moving or are you somewhere you can stop?",
  "intent": {
    "intent": "Harassment / Stalking",
    "confidence": 0.94,
    "urgency": "HIGH",
    "decision": "ESCALATE",
    "reasoning": "Caller explicitly states fear of being followed — high-threat pattern."
  },
  "timestamp": "2025-05-07T10:23:41"
}
```

---

## AI Agent Design

The AI plays **two simultaneous roles**:

**1. Caller-facing voice** (`CALLER_AGENT_SYSTEM` prompt)
- Speaks directly to the person in distress
- Warm, calm, concise (2-4 sentences — this is a phone call)
- Naturally mixes Hindi if caller does
- Gives concrete safety actions

**2. Internal intent classifier** (`INTENT_ANALYSIS_SYSTEM` prompt)
- Returns structured JSON: intent, confidence, urgency, decision
- Runs in parallel with the caller response (no added latency)
- Conservative: when in doubt, ESCALATE > CONFIRM

**Decision logic:**
- `ESCALATE` → urgency=HIGH and confidence ≥ 0.70 → dispatch immediately
- `CONFIRM`  → confidence < 0.65 or ambiguous → ask clarifying questions
- `PROCEED`  → urgency=MEDIUM/LOW and confidence ≥ 0.65 → standard protocol

---

## Swapping AI providers

The `SPASHTAgent` class in `ai_agent.py` is the only file to change.

**Switch to Gemini Flash (also free):**
```python
# pip install google-generativeai
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
self.client = genai.GenerativeModel("gemini-1.5-flash")
```

**Switch to Claude (best quality, paid):**
```python
# pip install anthropic
import anthropic
self.client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
self.model = "claude-3-5-haiku-20241022"  # fastest/cheapest Claude
```

---

## Production Checklist

- [ ] Set `GROQ_API_KEY` as a real environment variable (not in .env)
- [ ] Restrict CORS origins in `main.py` (`allow_origins=["https://yourdomain.com"]`)
- [ ] Swap SQLite → PostgreSQL via asyncpg for multi-server deployments
- [ ] Add rate limiting (e.g. slowapi) to `/chat` endpoint
- [ ] Add authentication (API key header) for operator dashboard
- [ ] Run behind nginx + SSL (certbot)
- [ ] Use `gunicorn -k uvicorn.workers.UvicornWorker` for production serving
