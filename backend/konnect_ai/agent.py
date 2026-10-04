"""Unified KonnectAI agent loop orchestrating STT, translation, classification, tools, and SMS."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from core_up.utils import send_sms
from .audit import check_rate_limit, log_tool_call
from .classifier import classify_intent
from .gemini import GeminiClient
from .memory import SessionMemory
from .models import ConversationSession
from .toolsets import FMS_TOOLS, GENERAL_TOOLS, POS_TOOLS, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are KonnectAI, a friendly, patient, voice-and-text agricultural assistant for Kenyan farmers using the FarmKonnect platform.

LANGUAGES:
- You always reply in English internally. The server translates your reply to the farmer's language before it reaches them.

STYLE:
- Short, spoken-style sentences. Never use bullet points, markdown tables, or numbered lists because your output is read aloud via speech synthesis.
- Warm, respectful, clear tone. Use 'you', never refer to 'the user'.
- Ask one question at a time.
- Never invent farm or financial numbers. If you need data, call a read tool.

SAFETY & CONFIRMATION:
- For ANY write tool (recording a sale, purchase, farm, crop, planting, input, harvest, or disease report), you MUST FIRST repeat the exact details back to the farmer as a single sentence and ask 'Should I save this?' without executing the tool.
- ONLY call the write tool with confirm=True after the farmer has clearly agreed ('yes', 'ndio', 'sawa', 'go ahead', 'save it', 'record it').
- Never delete records. Never ask for or record passwords or payment PINs.

ROUTING & BEHAVIOR:
- The server provides the detected intent (FMS, POS, or GENERAL) and relevant farm context.
- When you execute a write tool, conclude your response with a short reassuring confirmation of what changed. The server will automatically dispatch an SMS confirmation.
"""


def summarize_farmer_data(user) -> str:
    """Generate a compact summary of the farmer's active profile and assets."""
    profile = getattr(user, "farmer_profile", None)
    if not profile:
        return "No farmer profile completed yet."

    farms_count = profile.farms.count()
    sales_count = profile.sales.count()
    return f"Farmer {profile.full_name}, County: {profile.county or 'Unspecified'}, Farms: {farms_count}, Past Sales: {sales_count}"


def build_fms_context(user) -> str:
    """Build context text for Farm Management System operations."""
    profile = getattr(user, "farmer_profile", None)
    if not profile:
        return "Farmer has no profile registered yet."

    farms = list(profile.farms.values("id", "name", "size", "size_unit"))
    farms_desc = ", ".join([f"{f['name']} ({f['size']} {f['size_unit']})" for f in farms]) or "None"
    return f"Farmer: {profile.full_name}. Active farms: {farms_desc}. County: {profile.county}."


def build_pos_context(user) -> str:
    """Build context text for Point of Sale operations."""
    profile = getattr(user, "farmer_profile", None)
    name = profile.full_name if profile else user.username
    recent_sales = list(profile.sales.order_by("-date")[:3].values("product", "amount")) if profile else []
    sales_desc = ", ".join([f"{s['product']} (KES {s['amount']})" for s in recent_sales]) or "None"
    return f"Store Owner: {name}. Recent sales transactions: {sales_desc}."


def build_general_context(user) -> str:
    """Build general platform context."""
    return f"User: {user.username}, Phone: {getattr(user, 'phone', 'N/A')}."


def detect_language(text: str, default: str = "auto") -> str:
    """Detect whether user text is predominantly Swahili or English."""
    if default in ("sw", "en"):
        return default

    t = text.lower()
    sw_markers = [
        "habari", "jambo", "nimeuza", "nimepanda", "shamba", "mahindi",
        "mbolea", "gunia", "magunia", "bei", "mteja", "pesa", "elfu",
        "sawa", "ndio", "mavuno", "ugonjwa", "dawa", "kwa", "ya", "za", "na"
    ]
    sw_count = sum(1 for m in sw_markers if m in t.split())
    return "sw" if sw_count >= 1 else "en"


def run_turn(
    session: ConversationSession,
    user_text_local: str,
    lang: str = "auto",
    page: str = "dashboard",
    gemini_client: GeminiClient | None = None,
) -> Dict[str, Any]:
    """Execute a single conversational turn in KonnectAI:
    1. Language detection and translation (sw -> en).
    2. Intent classification (FMS | POS | GENERAL).
    3. Toolset selection and context assembly.
    4. Gemini function calling.
    5. Tool execution inside atomic transaction and audit logging.
    6. SMS dispatch for written transactions.
    7. Translation of reply back to farmer's language (en -> sw).
    """
    client = gemini_client or GeminiClient()
    memory = SessionMemory(session)
    user = session.user

    # 1. Determine language
    detected_lang = detect_language(user_text_local, default=lang)
    session.language = detected_lang
    session.save(update_fields=["language"])

    # Translate to English for internal processing
    user_text_en = client.translate(user_text_local, src="sw", tgt="en") if detected_lang == "sw" else user_text_local

    # Record user turn in memory
    memory.add_user_turn(text=user_text_en, lang=detected_lang, original_text=user_text_local)

    # 2. Check hourly tool call rate limit
    if not check_rate_limit(user, max_calls_per_hour=60):
        warning_en = "You have reached the maximum number of requests for this hour. Please try again later."
        warning_local = "Umefikia kikomo cha maombi kwa saa hii. Tafadhali jaribu tena baadaye." if detected_lang == "sw" else warning_en
        memory.add_ai_turn(text=warning_en, lang=detected_lang, text_local=warning_local)
        return {
            "reply": warning_local,
            "reply_en": warning_en,
            "intent": "GENERAL",
            "tool_calls": [],
            "sms_sent": False,
        }

    # 3. Classify intent
    classification = classify_intent(
        user_text_en=user_text_en,
        page=page,
        last_turns=memory.get_last_turns(3),
        farmer_summary=summarize_farmer_data(user),
        gemini_client=client,
    )
    intent = classification.get("intent", "GENERAL")
    confidence = classification.get("confidence", 0.9)

    # Low-confidence clarification check (< 0.6)
    if confidence < 0.6:
        clarification_en = "Is this request about your farm management records or about a sale or stock in the POS?"
        clarification_local = (
            "Je, ombi hili linahusu kumbukumbu zako za shamba au mauzo na bidhaa za dukani kwenye POS?"
            if detected_lang == "sw"
            else clarification_en
        )
        memory.add_ai_turn(text=clarification_en, lang=detected_lang, text_local=clarification_local, intent=intent)
        return {
            "reply": clarification_local,
            "reply_en": clarification_en,
            "intent": intent,
            "tool_calls": [],
            "sms_sent": False,
        }

    # 4. Load context and toolset based on intent
    if intent == "FMS":
        tools = FMS_TOOLS
        context = build_fms_context(user)
    elif intent == "POS":
        tools = POS_TOOLS
        context = build_pos_context(user)
    else:
        tools = GENERAL_TOOLS
        context = build_general_context(user)

    # 5. Call Gemini
    reply_en, tool_calls = client.chat(
        system=SYSTEM_PROMPT,
        history=memory.history,
        user=user_text_en,
        context=context,
        tools=tools,
        intent=intent,
    )

    # 6. Execute tool calls and log audit trail
    executed_results = []
    sms_sent_any = False

    for call in tool_calls:
        res = execute_tool(user, call)
        executed_results.append({
            "name": call.get("name"),
            "args": call.get("args"),
            "ok": res.get("ok", False),
            "wrote": res.get("wrote", False),
            "summary": res.get("summary_en", ""),
        })

        # Log audit entry
        log_tool_call(
            user=user,
            tool_name=call.get("name"),
            args=call.get("args", {}),
            ok=res.get("ok", False),
            result=res.get("data"),
            intent=intent,
            session=session,
        )

        # 7. Dispatch SMS confirmation if transaction was written
        if res.get("wrote") and res.get("sms_text_local"):
            sms_body = res["sms_text_local"]
            phone = getattr(user, "phone", "")
            if phone:
                sms_res = send_sms(phone, sms_body)
                if sms_res.get("ok"):
                    sms_sent_any = True
                    memory.mark_sms_sent()

    # 8. Translate response back to farmer's language
    reply_local = client.translate(reply_en, src="en", tgt="sw") if detected_lang == "sw" else reply_en

    # Record AI turn in session memory
    memory.add_ai_turn(
        text=reply_en,
        lang=detected_lang,
        text_local=reply_local,
        intent=intent,
        tool_calls=executed_results,
    )

    return {
        "reply": reply_local,
        "reply_en": reply_en,
        "intent": intent,
        "tool_calls": executed_results,
        "sms_sent": sms_sent_any,
    }
