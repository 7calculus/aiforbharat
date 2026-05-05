from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from .risk_engine import Decision, Urgency, decide_action, get_decision_color
except ImportError:
    from risk_engine import Decision, Urgency, decide_action, get_decision_color


app = FastAPI(
    title="SPASHT AI Backend",
    description="Prototype backend for simulated 1092 emergency call analysis.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Simulated caller speech")


class IntentRule(BaseModel):
    keywords: List[str]
    intent: str
    urgency: Urgency
    confidence: float = Field(..., ge=0, le=1)


class AnalyzeResponse(BaseModel):
    intent: str
    confidence: float
    urgency: Urgency
    decision: Decision
    color: str


INTENT_MAP: List[IntentRule] = [
    IntentRule(
        keywords=["broke into", "break-in", "break in", "intruder", "robbery"],
        intent="Property Crime / Break-In",
        urgency=Urgency.HIGH,
        confidence=0.8,
    ),
    IntentRule(
        keywords=["follow", "following", "stalker", "stalking", "scared", "help me", "danger"],
        intent="Harassment / Stalking",
        urgency=Urgency.HIGH,
        confidence=0.94,
    ),
    IntentRule(
        keywords=["fight", "hitting", "punch", "violence", "attack", "weapon", "knife", "gun"],
        intent="Physical Violence",
        urgency=Urgency.HIGH,
        confidence=0.91,
    ),
    IntentRule(
        keywords=["fire", "burning", "smoke", "explosion"],
        intent="Fire / Explosion",
        urgency=Urgency.HIGH,
        confidence=0.89,
    ),
    IntentRule(
        keywords=["accident", "crash", "injured", "bleeding", "unconscious"],
        intent="Medical Emergency",
        urgency=Urgency.HIGH,
        confidence=0.88,
    ),
    IntentRule(
        keywords=["argument", "shouting", "yelling", "noise", "disturbance"],
        intent="Disturbance / Dispute",
        urgency=Urgency.MEDIUM,
        confidence=0.75,
    ),
    IntentRule(
        keywords=["suspicious", "strange", "weird", "unsure", "don't know", "maybe", "wrong", "not sure"],
        intent="Suspicious Activity",
        urgency=Urgency.MEDIUM,
        confidence=0.58,
    ),
    IntentRule(
        keywords=["helpline", "information", "services", "number"],
        intent="Information / Helpline Services",
        urgency=Urgency.LOW,
        confidence=0.9,
    ),
    IntentRule(
        keywords=["lost", "missing", "theft", "stolen"],
        intent="Property Crime",
        urgency=Urgency.MEDIUM,
        confidence=0.72,
    ),
]


FALLBACK_RESPONSE = AnalyzeResponse(
    intent="Unknown / Unclear",
    confidence=0.31,
    urgency=Urgency.LOW,
    decision=Decision.CONFIRM,
    color=get_decision_color(Decision.CONFIRM),
)


def analyze_text(text: str) -> AnalyzeResponse:
    lower_text = text.lower()

    for rule in INTENT_MAP:
        if any(keyword in lower_text for keyword in rule.keywords):
            decision = decide_action(rule.urgency, rule.confidence)
            return AnalyzeResponse(
                intent=rule.intent,
                confidence=rule.confidence,
                urgency=rule.urgency,
                decision=decision,
                color=get_decision_color(decision),
            )

    return FALLBACK_RESPONSE


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "spasht-ai-backend"}


@app.get("/mock-intent", response_model=List[IntentRule])
def list_mock_intents() -> List[IntentRule]:
    return INTENT_MAP


@app.post("/mock-intent", response_model=AnalyzeResponse)
def mock_intent(request: AnalyzeRequest) -> AnalyzeResponse:
    return analyze_text(request.text)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    return analyze_text(request.text)
