# SPASHT AI Backend

FastAPI backend for the SPASHT AI prototype. It accepts simulated caller text, detects a mock emergency intent, assigns confidence and urgency, and returns the decision that the frontend dashboard displays.

This repository contains only the backend work. Frontend UI and data science/test datasets are handled by other teammates.

## Project Structure

```text
src/
  spasht_backend/
    __init__.py
    main.py
    risk_engine.py
requirements.txt
pyproject.toml
README.md
```

## Setup

```powershell
cd C:\Users\Vanshika\aiforbharat
python -m pip install -r requirements.txt
```

## Run Server

```powershell
python -m uvicorn spasht_backend.main:app --reload --app-dir src
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

### GET `/`

Health check.

Response:

```json
{
  "status": "ok",
  "service": "spasht-ai-backend"
}
```

### GET `/mock-intent`

Returns the backend's hardcoded keyword-to-intent rules.

### POST `/mock-intent`

Analyzes text using the mock intent rules.

Request:

```json
{
  "text": "There is a fight happening near my house"
}
```

Response:

```json
{
  "intent": "Physical Violence",
  "confidence": 0.91,
  "urgency": "HIGH",
  "decision": "ESCALATE",
  "color": "red"
}
```

### POST `/analyze`

Main endpoint for the frontend dashboard.

Request:

```json
{
  "text": "Someone is following me, I am scared"
}
```

Response:

```json
{
  "intent": "Harassment / Stalking",
  "confidence": 0.94,
  "urgency": "HIGH",
  "decision": "ESCALATE",
  "color": "red"
}
```

## Decision Rules

- `HIGH` urgency -> `ESCALATE`
- confidence below `0.65` -> `CONFIRM`
- otherwise -> `PROCEED`

## Frontend Integration

```js
const res = await fetch("http://127.0.0.1:8000/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text }),
});

const result = await res.json();
```
