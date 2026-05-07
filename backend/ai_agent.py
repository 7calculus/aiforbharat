"""
SPASHT AI Agent
Uses Groq (Llama 3.3-70b-versatile) — free, ultra-fast inference.
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

LANGUAGE RULES — this is critical:
- If the caller writes in Kannada (ಕನ್ನಡ) or uses Kannada words → respond FULLY in Kannada
- If the caller writes in Hindi or mixes Hindi → respond in Hindi or Hinglish
- If the caller writes in English → respond in English
- If the caller mixes Kannada and English (Kanglish) → match their mix naturally
- You understand local Kannada slang, dialects from Bangalore, Mysore, Dharwad, Hubli, Mangalore
- Common Kannada emergency phrases you understand: "help maadi", "bayam aagatte", "odidare", "hogbedi", "police kariyri", "nanu safe illa", "yaavdo follow maadtidaane"

Your personality:
- Calm, warm, and reassuring — never cold or robotic
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
- If the situation is clearly violent/life-threatening, say help is being dispatched RIGHT NOW
- Always end with a question or instruction to keep the caller engaged
- If caller goes quiet, prompt gently in their language

Location: {location}
"""

INTENT_ANALYSIS_SYSTEM = """You are an emergency call intent classifier for India's 1092 helpline.
Analyze the caller's message and conversation history. The message may be in English, Hindi, Kannada, or a mix.

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "intent": "<one of: Physical Violence | Harassment / Stalking | Fire / Explosion | Medical Emergency | Disturbance / Dispute | Suspicious Activity | Property Crime | Sexual Assault | Child in Danger | Unknown / Unclear>",
  "confidence": <float 0.0-1.0>,
  "urgency": "<HIGH | MEDIUM | LOW>",
  "decision": "<ESCALATE | CONFIRM | PROCEED>",
  "reasoning": "<one sentence explaining the classification>"
}

Decision rules:
- ESCALATE: urgency=HIGH and confidence >= 0.80 AND there is a clear immediate threat (weapon, violence, active attack)
- CONFIRM: confidence < 0.70 OR situation is vague, unclear, or caller is just worried — ask clarifying questions first
- PROCEED: urgency=MEDIUM/LOW and confidence >= 0.70 → handle via standard protocol

Be ACCURATE not paranoid. Do NOT escalate just because someone sounds scared or worried.
Only ESCALATE when there is strong evidence of immediate physical danger.
If in doubt → always CONFIRM first, never ESCALATE blindly.

Kannada keywords that indicate HIGH urgency only if combined with clear threat: bayam, help maadi, odidare, follow maadtidaane, hogbedi, safe illa, yaavdo, hudugaru, hanikara
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
        self.model = "llama-3.3-70b-versatile"

    def _build_caller_messages(self, caller_message, location, history):
        system = CALLER_AGENT_SYSTEM.format(location=location or "Unknown location")
        messages = [{"role": "system", "content": system}]
        for entry in history:
            role = "user" if entry.role == "caller" else "assistant"
            if entry.role == "system":
                continue
            messages.append({"role": role, "content": entry.content})
        messages.append({"role": "user", "content": caller_message})
        return messages

    def _build_analysis_messages(self, text, history):
        history_text = "\n".join(
            f"{e.role.upper()}: {e.content}" for e in history[-6:]
        )
        prompt = f"Conversation history:\n{history_text}\n\nLatest message: {text}"
        return [
            {"role": "system", "content": INTENT_ANALYSIS_SYSTEM},
            {"role": "user",   "content": prompt},
        ]

    async def stream_response(self, session_id, caller_message, location, history):
        messages = self._build_caller_messages(caller_message, location, history)
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=200,
            temperature=0.6,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def full_response(self, session_id, caller_message, location, history):
        messages = self._build_caller_messages(caller_message, location, history)
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

    async def analyze_intent(self, text, history):
        messages = self._build_analysis_messages(text, history)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=300,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
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
            return IntentResult(
                intent="Unknown / Unclear",
                confidence=0.31,
                urgency="LOW",
                decision="CONFIRM",
                reasoning="Could not parse AI response; defaulting to CONFIRM.",
            )