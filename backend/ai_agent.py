"""
SPASHT AI Agent
Uses Groq (Llama 3.3-70b-versatile) — free, ultra-fast inference.

The agent plays two roles:
  1. Empathetic AI voice that speaks TO the person in distress
  2. Internal intent analyzer that classifies and produces dispatch decisions

Swap to Gemini: replace client init + model name; the prompt logic stays identical.
"""

import os
import json
import re
import asyncio
from typing import AsyncGenerator, Optional, List, Tuple

from groq import AsyncGroq
from models import IntentResult, HistoryEntry

# ── System prompts ─────────────────────────────────────────────────────────────

CALLER_AGENT_SYSTEM = """You are SPASHT, an AI emergency dispatch agent for India's 1092 women's helpline.
You are speaking DIRECTLY to a person who may be in danger or distress.

Your personality:
- Calm, warm, and reassuring — never cold or robotic
- Speak in simple, clear language (mix Hindi words naturally if caller does)
- Always prioritise their safety over gathering information
- Never panic or use alarming language that could escalate their fear

Your responsibilities in order:
1. ACKNOWLEDGE their distress immediately and make them feel heard
2. ASSESS the situation — gently ask where they are, what is happening
3. REASSURE them that help is coming / they are not alone
4. GUIDE them — give concrete safety actions (lock door, move to public area, stay on line)
5. KEEP THEM CALM until help arrives

Rules:
- NEVER say you are an AI model unless directly asked — stay in character as a calm dispatcher
- Keep responses SHORT (2-4 sentences max) — this is a phone call, not a chat
- If the situation is clearly violent/life-threatening, say "Help is being dispatched to you RIGHT NOW"
- Always end with a question or instruction to keep the caller engaged and responding
- If caller goes quiet, prompt gently: "Are you still there? I'm with you."

Location: {location}
"""

INTENT_ANALYSIS_SYSTEM = """You are an emergency call intent classifier for India's 1092 helpline.
Analyze the caller's message and conversation history.

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "intent": "<one of: Physical Violence | Harassment / Stalking | Fire / Explosion | Medical Emergency | Disturbance / Dispute | Suspicious Activity | Property Crime | Sexual Assault | Child in Danger | Unknown / Unclear>",
  "confidence": <float 0.0-1.0>,
  "urgency": "<HIGH | MEDIUM | LOW>",
  "decision": "<ESCALATE | CONFIRM | PROCEED>",
  "reasoning": "<one sentence explaining the classification>"
}

Decision rules:
- ESCALATE: urgency=HIGH and confidence >= 0.70 → dispatch immediately
- CONFIRM: confidence < 0.65 OR situation ambiguous → ask clarifying questions  
- PROCEED: urgency=MEDIUM/LOW and confidence >= 0.65 → handle via standard protocol

Be conservative: when in doubt, ESCALATE rather than CONFIRM.
"""

# ── Agent class ───────────────────────────────────────────────────────────────

class SPASHTAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Get a free key at https://console.groq.com"
            )
        self.client = AsyncGroq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"   # best free model on Groq
        # self.model = "gemma2-9b-it"             # lighter alternative

    def _build_caller_messages(
        self,
        caller_message: str,
        location: Optional[str],
        history: List[HistoryEntry],
    ) -> list:
        system = CALLER_AGENT_SYSTEM.format(location=location or "Unknown location")
        messages = [{"role": "system", "content": system}]

        for entry in history:
            role = "user" if entry.role == "caller" else "assistant"
            if entry.role == "system":
                continue
            messages.append({"role": role, "content": entry.content})

        messages.append({"role": "user", "content": caller_message})
        return messages

    def _build_analysis_messages(
        self,
        text: str,
        history: List[HistoryEntry],
    ) -> list:
        history_text = "\n".join(
            f"{e.role.upper()}: {e.content}" for e in history[-6:]  # last 6 turns
        )
        prompt = f"Conversation history:\n{history_text}\n\nLatest message: {text}"
        return [
            {"role": "system", "content": INTENT_ANALYSIS_SYSTEM},
            {"role": "user",   "content": prompt},
        ]

    # ── Public API ────────────────────────────────────────────────────────────

    async def stream_response(
        self,
        session_id: str,
        caller_message: str,
        location: Optional[str],
        history: List[HistoryEntry],
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive from Groq."""
        messages = self._build_caller_messages(caller_message, location, history)
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=200,        # keep responses concise for a call
            temperature=0.6,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def full_response(
        self,
        session_id: str,
        caller_message: str,
        location: Optional[str],
        history: List[HistoryEntry],
    ) -> Tuple[str, Optional[IntentResult]]:
        """Get full AI response + intent analysis in parallel."""
        messages = self._build_caller_messages(caller_message, location, history)

        # Run both requests concurrently
        chat_task = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=200,
            temperature=0.6,
        )
        intent_task = self.analyze_intent(caller_message, history)

        chat_response, intent = await asyncio.gather(chat_task, intent_task)
        ai_text = chat_response.choices[0].message.content
        return ai_text, intent

    async def analyze_intent(
        self,
        text: str,
        history: List[HistoryEntry],
    ) -> IntentResult:
        """Classify intent, urgency, and decision from caller message."""
        messages = self._build_analysis_messages(text, history)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=300,
            temperature=0.1,    # low temp = consistent structured output
        )
        raw = response.choices[0].message.content.strip()

        # Strip any accidental markdown fences
        raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()

        try:
            data = json.loads(raw)
            return IntentResult(
                intent=data.get("intent", "Unknown / Unclear"),
                confidence=float(data.get("confidence", 0.5)),
                urgency=data.get("urgency", "MEDIUM"),
                decision=data.get("decision", "CONFIRM"),
                reasoning=data.get("reasoning"),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Graceful fallback — never crash on bad AI output
            return IntentResult(
                intent="Unknown / Unclear",
                confidence=0.31,
                urgency="LOW",
                decision="CONFIRM",
                reasoning="Could not parse AI response; defaulting to CONFIRM.",
            )
