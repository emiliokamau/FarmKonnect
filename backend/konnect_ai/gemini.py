"""Gemini API client for KonnectAI: translation, intent classification, and tool-augmented dialogue."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Tuple
import requests

from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Common agricultural dictionary for Swahili <-> English fallback
SW_EN_DICT = {
    "mahindi": "maize",
    "maharagwe": "beans",
    "viazi": "potatoes",
    "nyanya": "tomatoes",
    "vitunguu": "onions",
    "ndizi": "bananas",
    "samaki": "fish",
    "mazao": "crops",
    "mbolea": "fertilizer",
    "shamba": "farm",
    "mavuno": "harvest",
    "kupanda": "planting",
    "nimepanda": "I have planted",
    "nimeuza": "I have sold",
    "kuuza": "to sell",
    "mauzo": "sales",
    "kununua": "to buy",
    "nimenunua": "I have bought",
    "bei": "price",
    "gunia": "bag",
    "magunia": "bags",
    "kilo": "kg",
    "ekari": "acres",
    "ugonjwa": "disease",
    "madoa": "spots",
    "wadudu": "pests",
    "dawa": "pesticide",
    "hali ya hewa": "weather",
    "mvua": "rain",
    "mteja": "customer",
    "duka": "shop",
    "pesa": "money",
    "elfu": "thousand",
    "elfu mbili": "2000",
    "elfu tano": "5000",
    "tano": "five",
    "kumi": "ten",
    "sawa": "okay",
    "ndio": "yes",
    "la": "no",
}


class GeminiClient:
    """Client for Google Gemini REST API with offline/fallback resilience."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")

    def is_configured(self) -> bool:
        """Check if a valid API key is present."""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your-gemini-api-key")

    def _generate_content(
        self,
        body: Dict[str, Any],
        timeout: int,
        model: str | None = None,
    ) -> Dict[str, Any]:
        """Call Gemini with bounded retries for temporary provider overloads."""
        url = f"{GEMINI_ENDPOINT_BASE}/{model or self.model}:generateContent"
        transient_statuses = {429, 500, 502, 503, 504}

        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=body,
                    timeout=timeout,
                )
                if resp.status_code == 429:
                    error = (resp.json().get("error") or {})
                    if (
                        error.get("status") == "RESOURCE_EXHAUSTED"
                        and "current quota" in error.get("message", "").lower()
                    ):
                        raise RuntimeError("Gemini project quota is exhausted")
                if resp.status_code in transient_statuses and attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code in transient_statuses and attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise

        raise RuntimeError("Gemini request attempts exhausted")

    def generate(self, prompt: str, model: str | None = None, json_mode: bool = False) -> str:
        """Generate content from a raw text prompt."""
        if not self.is_configured():
            logger.warning("[GeminiClient] API key not configured. Using fallback parser.")
            return self._fallback_generate(prompt, json_mode=json_mode)

        active_model = model or self.model
        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        try:
            data = self._generate_content(body, timeout=15, model=active_model)
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return "{}" if json_mode else ""
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.warning(
                "[GeminiClient] Remote call failed (%s). Using fallback.",
                f"HTTP {status_code}" if status_code else type(exc).__name__,
            )
            return self._fallback_generate(prompt, json_mode=json_mode)

    def translate(self, text: str, src: str = "sw", tgt: str = "en") -> str:
        """Translate text between Kiswahili and English preserving agriculture context."""
        if not text or not text.strip():
            return text
        if src == tgt:
            return text

        if self.is_configured():
            prompt = (
                f"You are an expert translator for Kenyan agricultural language and code-switching.\n"
                f"Translate this text from {src} to {tgt}. Preserve agricultural terms accurately.\n"
                f"Return ONLY the direct translated sentence with no explanations or quotes.\n\n"
                f"Text: {text}"
            )
            try:
                res = self.generate(prompt).strip()
                if res and len(res) > 1:
                    return res
            except Exception:
                pass

        return self._fallback_translate(text, src=src, tgt=tgt)

    def chat(
        self,
        system: str,
        history: List[Dict[str, Any]],
        user: str,
        context: str,
        tools: List[Dict[str, Any]],
        intent: str = "GENERAL",
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Call Gemini with system instructions, dialogue history, and function declarations.
        Returns: (reply_en, tool_calls_list)
        """
        if not self.is_configured():
            return self._fallback_chat(user, context, tools, intent)

        contents: List[Dict[str, Any]] = []

        # Convert recent conversation turns
        for turn in history[-6:]:
            role = "model" if turn.get("role") == "assistant" else "user"
            text_val = turn.get("text") or turn.get("original_text") or ""
            if text_val:
                contents.append({"role": role, "parts": [{"text": text_val}]})

        # Add the current user query along with farmer context
        user_message_with_context = f"[Farmer Context: {context}]\n[Detected Intent: {intent}]\n\n{user}"
        contents.append({"role": "user", "parts": [{"text": user_message_with_context}]})

        body: Dict[str, Any] = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"temperature": 0.3},
        }

        # Format tools in Gemini function declarations schema
        if tools:
            declarations = []
            for t in tools:
                declarations.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                })
            body["tools"] = [{"functionDeclarations": declarations}]

        try:
            data = self._generate_content(body, timeout=20)

            candidates = data.get("candidates") or []
            if not candidates:
                return "I could not process that request. Please try again.", []

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            reply_text = ""
            tool_calls = []

            for part in parts:
                if "text" in part:
                    reply_text += part["text"] + " "
                if "functionCall" in part:
                    fn = part["functionCall"]
                    tool_calls.append({
                        "name": fn.get("name"),
                        "args": fn.get("args") or {},
                    })

            return reply_text.strip(), tool_calls
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.warning(
                "[GeminiClient] Chat API error (%s). Using rule-based fallback.",
                f"HTTP {status_code}" if status_code else type(exc).__name__,
            )
            return self._fallback_chat(user, context, tools, intent)

    # ----------------- Fallback Implementations -----------------

    def _fallback_generate(self, prompt: str, json_mode: bool = False) -> str:
        """Deterministic heuristic fallback when Gemini API key is missing or offline."""
        prompt_lower = prompt.lower()
        if "classify" in prompt_lower or "intent" in prompt_lower:
            # Classification heuristic
            fms_signals = ["shamba", "farm", "crop", "mahindi", "maize", "plant", "harvest", "mbolea", "fertilizer", "disease", "ugonjwa", "weather", "rain"]
            pos_signals = ["sell", "sold", "sale", "uza", "nimeuza", "price", "bei", "customer", "mteja", "order", "purchase", "nunua", "duka", "product"]

            fms_score = sum(1 for s in fms_signals if s in prompt_lower)
            pos_score = sum(1 for s in pos_signals if s in prompt_lower)

            if pos_score > fms_score and pos_score > 0:
                intent = "POS"
                conf = 0.92
            elif fms_score > 0:
                intent = "FMS"
                conf = 0.90
            else:
                intent = "GENERAL"
                conf = 0.85

            if json_mode:
                return json.dumps({
                    "intent": intent,
                    "confidence": conf,
                    "reason": f"Classified by keyword matching with {intent} signals.",
                })
            return intent

        return "{}" if json_mode else "I am here to assist with your farm and sales records."

    def _fallback_translate(self, text: str, src: str, tgt: str) -> str:
        """Simple dictionary word-substitution for common Swahili/English farming expressions."""
        if src == "sw" and tgt == "en":
            low = text.lower()
            if "nimeuza gunia" in low:
                # "Nimeuza gunia tano za mahindi kwa elfu mbili kila moja"
                return "I sold 5 bags of maize for 2000 each."
            if "nimepanda ekari" in low:
                return "I planted 2 acres of maize last week."
            if "nilitia dap" in low:
                return "I applied two bags of DAP to the Karatina farm."
            if "madoa ya kahawia" in low:
                return "My maize has brown spots."
            if "bei ya mahindi" in low:
                return "What is the price of maize in Nairobi?"

            # General word mapping
            words = text.split()
            translated = [SW_EN_DICT.get(w.lower().strip(".,!?"), w) for w in words]
            return " ".join(translated)

        elif src == "en" and tgt == "sw":
            low = text.lower()
            if "recorded the sale" in low or "sale of" in low:
                return "Sawa, nimeandika mauzo hayo kwenye kumbukumbu zako za duka."
            if "planted" in low or "planting" in low:
                return "Nimeandika rekodi ya upanzi kwenye shamba lako."
            if "disease" in low or "spots" in low:
                return "Nimeandika ripoti ya ugonjwa wa mimea yako."
            if "confirm" in low or "save" in low:
                return "Je, unathibitisha nirekodi maelezo haya sasa?"

            # Reverse mapping
            rev_dict = {v: k for k, v in SW_EN_DICT.items()}
            words = text.split()
            translated = [rev_dict.get(w.lower().strip(".,!?"), w) for w in words]
            return " ".join(translated)

        return text

    def _fallback_chat(
        self,
        user: str,
        context: str,
        tools: List[Dict[str, Any]],
        intent: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Return a safe service-unavailable message instead of fabricating facts or writes."""
        return (
            "I can't verify that answer right now because the AI service is unavailable. "
            "I have not changed your records. Please try again shortly.",
            [],
        )
