"""Gemini-powered intent classifier for KonnectAI."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
from .gemini import GeminiClient

logger = logging.getLogger(__name__)


def classify_intent(
    user_text_en: str,
    page: str = "dashboard",
    last_turns: List[Dict[str, Any]] | None = None,
    farmer_summary: str = "",
    gemini_client: GeminiClient | None = None,
) -> Dict[str, Any]:
    """Classify the user utterance into FMS, POS, or GENERAL using Gemini with structured JSON output."""
    client = gemini_client or GeminiClient()

    prompt = f"""
You are an intent classifier for a Kenyan agricultural portal called FarmKonnect.
Classify the farmer's message into exactly one of three categories:

1. FMS (Farm Management System)
   Signals: farms, fields, shamba, crops, maize, beans, planting, kupanda,
   harvest, mavuno, inputs, fertilizer, mbolea, disease, ugonjwa, weather,
   rain, extension visits, farm finance, farm equipment.

2. POS (Point of Sale & Commerce)
   Signals: sales, sell, uza, sold, bags, gunia, price for selling, customer,
   mteja, product, product stock, store inventory, purchases, supplier,
   orders, receipts, duka, biashara, payments.

3. GENERAL
   Signals: greetings, general questions about the app, ask for help,
   advisories, weather chat without farm context, broad inquiries.

Context:
- Current application page: {page} (Strong prior: 'pos' indicates POS; 'dashboard' indicates FMS)
- Last conversation turns: {json.dumps(last_turns or [])}
- Farmer's farm profile summary: {farmer_summary}

Farmer's Message (in English): "{user_text_en}"

Respond ONLY with valid JSON in this exact structure:
{{
  "intent": "FMS" | "POS" | "GENERAL",
  "confidence": 0.0 to 1.0,
  "reason": "one brief explanation sentence"
}}
"""
    try:
        raw_output = client.generate(prompt, json_mode=True)
        # Clean any surrounding markdown fences
        clean_json = raw_output.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(clean_json)
        intent = data.get("intent", "GENERAL").upper()
        if intent not in ("FMS", "POS", "GENERAL"):
            intent = "GENERAL"

        confidence = float(data.get("confidence", 0.8))
        reason = data.get("reason", "Classified based on semantic content.")

        return {
            "intent": intent,
            "confidence": min(max(confidence, 0.0), 1.0),
            "reason": reason,
        }
    except Exception as exc:
        logger.warning("[classify_intent] Classification failed or JSON parse error: %s. Using heuristics.", exc)
        return _fallback_rule_classifier(user_text_en, page)


def _fallback_rule_classifier(text: str, page: str) -> Dict[str, Any]:
    """Heuristic rule-based classifier when offline or during tests."""
    t = text.lower()

    # 1. Check greetings and general inquiries first
    greeting_words = ["hi", "hello", "habari", "mambo", "help", "nisaidie", "what can you do", "who are you"]
    if any(k in t for k in greeting_words):
        strong_actions = ["nimeuza", "nimepanda", "uza", "panda", "nunua", "harvest"]
        if not any(a in t for a in strong_actions):
            return {"intent": "GENERAL", "confidence": 0.85, "reason": "Greeting or general help."}

    pos_keywords = [
        "sell", "sold", "sale", "uza", "nimeuza", "customer", "mteja",
        "stock", "store", "purchase", "bought", "nunua", "pos", "duka",
        "receipt", "payment", "counter", "bag", "gunia", "order"
    ]
    fms_keywords = [
        "farm", "shamba", "crop", "plant", "planted", "harvest", "mavuno",
        "fertilizer", "mbolea", "dap", "can", "seed", "disease", "ugonjwa",
        "pest", "spots", "weather", "rain", "mvua", "acre", "ekari", "field"
    ]

    pos_hits = sum(1 for k in pos_keywords if k in t)
    fms_hits = sum(1 for k in fms_keywords if k in t)

    # Page bias applied only if signals or context queries present
    if pos_hits > 0 or fms_hits > 0 or any(k in t for k in ["receipt", "item", "record", "show", "summary"]):
        if page == "pos":
            pos_hits += 1
        elif page == "dashboard":
            fms_hits += 1

    if pos_hits > fms_hits and pos_hits > 0:
        return {"intent": "POS", "confidence": 0.90, "reason": "POS commerce signals detected."}
    elif fms_hits > pos_hits and fms_hits > 0:
        return {"intent": "FMS", "confidence": 0.90, "reason": "FMS agricultural signals detected."}
    elif fms_hits > 0 and pos_hits > 0:
        intent = "POS" if page == "pos" else "FMS"
        return {"intent": intent, "confidence": 0.75, "reason": f"Disambiguated by page {page}."}

    # Ambiguous or short text with 0 signals -> low confidence (<0.6)
    return {"intent": "GENERAL", "confidence": 0.50, "reason": "Ambiguous message requiring clarification."}
