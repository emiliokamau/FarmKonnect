import re
import base64
from typing import Any

import httpx
from django.conf import settings
from django.db import transaction

from .models import AgentAction, Conversation, Farmer


def classify_message(message: str) -> tuple[str, dict[str, Any]]:
    normalized = message.strip().lower()
    entities: dict[str, Any] = {}
    sale_terms = ("sold", "sale", "sold", "nimeuza", "kuuza")
    disease_terms = ("disease", "symptom", "sick", "spots", "ugonjwa", "majani")
    inventory_terms = ("stock", "inventory", "available", "mali")
    if any(term in normalized for term in sale_terms):
        intent = "SALE_RECORD"
        quantity = re.search(r"\b(\d+(?:\.\d+)?)\b", normalized)
        if quantity:
            entities["quantity"] = float(quantity.group(1))
    elif any(term in normalized for term in disease_terms):
        intent = "DISEASE_ADVISORY"
    elif any(term in normalized for term in inventory_terms):
        intent = "INVENTORY_LOOKUP"
    else:
        intent = "GENERAL_FARM_ADVISORY"
    return intent, entities


def build_farmer_context(farmer: Farmer) -> dict[str, Any]:
    farms = list(farmer.farms.prefetch_related("crop_records__disease_reports", "crop_records__harvests"))
    return {
        "farmer": {
            "farmer_id": str(farmer.farmer_id),
            "name": str(farmer),
            "county": farmer.county,
            "sub_county": farmer.sub_county,
            "preferred_language": farmer.preferred_language,
        },
        "farms": [
            {
                "farm_id": str(farm.farm_id),
                "farm_name": farm.farm_name,
                "acreage": str(farm.acreage) if farm.acreage is not None else None,
                "soil_type": farm.soil_type,
                "irrigation_available": farm.irrigation_available,
                "crops": [
                    {
                        "crop_record_id": str(crop.crop_record_id),
                        "crop_name": crop.crop_name,
                        "variety": crop.variety,
                        "status": crop.status,
                        "disease_reports": [report.symptoms for report in crop.disease_reports.all()],
                        "harvests": [str(harvest.quantity) for harvest in crop.harvests.all()],
                    }
                    for crop in farm.crop_records.all()
                ],
            }
            for farm in farms
        ],
        "inventory": [
            {"product": item.product_name, "quantity": str(item.quantity), "unit": item.unit}
            for item in farmer.inventory.all()
        ],
        "recent_sales": [
            {"product": sale.product_name, "quantity": str(sale.quantity), "unit": sale.unit, "total": str(sale.total_amount)}
            for sale in farmer.sales.order_by("-sale_date")[:10]
        ],
    }


def build_farmer_data(farmer: Farmer) -> dict[str, Any]:
    context = build_farmer_context(farmer)
    return {
        **context,
        "conversations": [
            {
                "conversation_id": str(conversation.conversation_id),
                "original_message": conversation.original_message,
                "normalized_message": conversation.normalized_message,
                "language_detected": conversation.language_detected,
                "intent": conversation.intent,
                "extracted_entities": conversation.extracted_entities,
                "ai_response": conversation.ai_response,
                "created_at": conversation.created_at.isoformat(),
            }
            for conversation in farmer.conversations.order_by("-created_at")[:50]
        ],
        "agent_actions": [
            {
                "action_id": str(action.action_id),
                "intent": action.intent,
                "target_module": action.target_module,
                "action_taken": action.action_taken,
                "status": action.status,
                "created_at": action.created_at.isoformat(),
            }
            for action in farmer.agent_actions.order_by("-created_at")[:50]
        ],
    }


@transaction.atomic
def respond_to_farmer(farmer: Farmer, message: str) -> dict[str, Any]:
    intent, entities = classify_message(message)
    context = build_farmer_context(farmer)
    response = (
        f"I understood this as {intent.replace('_', ' ').lower()}. "
        f"I found {len(context['farms'])} farm(s) and {len(context['inventory'])} inventory item(s) "
        f"for {farmer.first_name}."
    )
    conversation = Conversation.objects.create(
        farmer=farmer,
        original_message=message,
        normalized_message=message.strip().lower(),
        language_detected="sw" if any(word in message.lower() for word in ("nime", "ugonjwa", "kuuza")) else "en",
        intent=intent,
        extracted_entities=entities,
        ai_response=response,
    )
    AgentAction.objects.create(
        farmer=farmer,
        intent=intent,
        target_module="context_mapping",
        action_taken="Fetched farmer profile, farms, crops, inventory, and recent sales",
        status="completed",
    )
    return {
        "conversation_id": conversation.conversation_id,
        "farmer_id": farmer.farmer_id,
        "intent": intent,
        "context": context,
        "response": response,
    }


def transcribe_and_translate_audio(audio_file: Any) -> tuple[str, str, str, str]:
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured.")

    audio_file.seek(0)
    response = httpx.post(
        settings.ELEVENLABS_API_URL,
        headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
        data={
            "model_id": settings.ELEVENLABS_TRANSCRIPTION_MODEL,
            "language_code": "swa",
        },
        files={
            "file": (
                getattr(audio_file, "name", "audio-upload"),
                audio_file,
                getattr(audio_file, "content_type", "application/octet-stream"),
            )
        },
        timeout=120,
    )
    if response.is_error:
        raise RuntimeError(f"ElevenLabs transcription failed ({response.status_code}).")

    transcript = response.json().get("text", "").strip()
    if not transcript:
        raise ValueError("The audio file did not contain recognizable speech.")

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    translation_response = httpx.post(
        f"{settings.GEMINI_API_URL}/{settings.GEMINI_TRANSLATION_MODEL}:generateContent",
        params={"key": settings.GEMINI_API_KEY},
        json={
            "contents": [{
                "parts": [{
                    "text": (
                        "Translate the following Swahili farmer message to natural English. "
                        "Return only the English translation.\n\n"
                        f"Swahili: {transcript}"
                    )
                }]
            }],
            "generationConfig": {"temperature": 0},
        },
        timeout=60,
    )
    if translation_response.is_error:
        raise RuntimeError(f"Gemini translation failed ({translation_response.status_code}).")

    candidates = translation_response.json().get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    translation = "".join(part.get("text", "") for part in parts).strip()
    if not translation:
        raise ValueError("The audio transcript could not be translated.")

    if not settings.ELEVENLABS_VOICE_ID:
        raise RuntimeError("ELEVENLABS_VOICE_ID is not configured.")

    speech_response = httpx.post(
        f"{settings.ELEVENLABS_TTS_API_URL}/{settings.ELEVENLABS_VOICE_ID}",
        headers={
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        },
        json={
            "text": translation,
            "model_id": settings.ELEVENLABS_TTS_MODEL,
        },
        timeout=120,
    )
    if speech_response.is_error:
        raise RuntimeError(f"ElevenLabs speech generation failed ({speech_response.status_code}).")
    return transcript, translation, base64.b64encode(speech_response.content).decode("ascii"), "audio/mpeg"
