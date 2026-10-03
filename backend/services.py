"""Service layer for Farmkonnect backend.

The module isolates external concerns – price‑feed integration, AI advisory
generation and any heavy business logic – from the thin Django views.

* ``fetch_market_prices`` pulls daily price data from a configurable external
  API (KAMIS/KAOP). The function is deliberately generic; a concrete client can
  be swapped via environment variables.
* ``get_price_trend`` aggregates historic ``MarketPrice`` rows for a commodity
  and county, returning a list of ``{"date": str, "wholesale": Decimal,
  "retail": Decimal}`` dictionaries suitable for charting.
* ``generate_advisory`` prepares a price snapshot, calls the AI model (here
  represented by a simple HTTP request to a configurable endpoint) and stores
  the recommendation on the ``AdvisoryRequest`` instance.

All public functions are type‑annotated and raise domain‑specific
exceptions for easier testing.
"""

import os
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

import requests
from django.conf import settings
from django.db import transaction

from .models import MarketPrice, Commodity, County, AdvisoryRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# External price‑feed integration
# ---------------------------------------------------------------------------

PRICE_API_URL = os.getenv("MARKET_PRICE_API_URL", "https://api.example.com/price")
API_KEY = os.getenv("MARKET_PRICE_API_KEY")


def _call_price_api(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Low‑level wrapper around the external price API.

    Parameters
    ----------
    payload:
        JSON payload expected by the third‑party service.

    Returns
    -------
    List[Dict[str, Any]]
        A list of raw price records as defined by the provider.
    """
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    response = requests.post(PRICE_API_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json().get("data", [])


def fetch_market_prices(commodity_code: str, date: datetime) -> None:
    """Fetch and persist daily market prices for a given commodity.

    The function is intended to be called from a Celery beat task on a daily
    schedule. It resolves the ``Commodity`` instance, builds the API request, and
    stores each returned price record as a ``MarketPrice`` row.
    """
    try:
        commodity = Commodity.objects.get(code=commodity_code.upper())
    except Commodity.DoesNotExist as exc:
        logger.error("Commodity %s not found", commodity_code)
        raise exc

    payload = {"commodity": commodity.code, "date": date.strftime("%Y-%m-%d")}
    raw_prices = _call_price_api(payload)

    for entry in raw_prices:
        county_name = entry.get("county")
        try:
            county = County.objects.get(name__iexact=county_name)
        except County.DoesNotExist:
            logger.warning("Skipping unknown county %s", county_name)
            continue

        MarketPrice.objects.update_or_create(
            commodity=commodity,
            county=county,
            date=date,
            defaults={
                "wholesale_price": Decimal(entry["wholesale_price"]),
                "retail_price": Decimal(entry["retail_price"]),
            },
        )

# ---------------------------------------------------------------------------
# Price trend helper used by API viewsets
# ---------------------------------------------------------------------------

def get_price_trend(
    commodity_code: str, county_name: str, days: int = 30
) -> List[Dict[str, Any]]:
    """Return a time series of market prices.

    Parameters
    ----------
    commodity_code:
        Short commodity identifier (e.g. ``MAIZE``).
    county_name:
        Exact county name as stored in the ``County`` table.
    days:
        Number of past days to include. Defaults to 30.
    """
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=days)
    prices = (
        MarketPrice.objects.filter(
            commodity__code=commodity_code.upper(),
            county__name__iexact=county_name,
            date__range=(start_date, end_date),
        )
        .order_by("date")
        .values("date", "wholesale_price", "retail_price")
    )
    return [
        {
            "date": p["date"].isoformat(),
            "wholesale": str(p["wholesale_price"]),
            "retail": str(p["retail_price"]),
        }
        for p in prices
    ]

# ---------------------------------------------------------------------------
# AI advisory wrapper
# ---------------------------------------------------------------------------

AI_ENDPOINT = os.getenv("AI_ADVISORY_ENDPOINT", "https://api.openai.com/v1/completions")
AI_API_KEY = os.getenv("AI_ADVISORY_KEY")


def _call_ai(prompt: str) -> str:
    """Send a prompt to the configured LLM and return the raw text.
    """
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": os.getenv("AI_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
    }
    response = requests.post(AI_ENDPOINT, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


@transaction.atomic
def generate_advisory(request_id: int) -> AdvisoryRequest:
    """Process an ``AdvisoryRequest`` and store the AI recommendation.

    The function:
    1. Retrieves the request and the latest market price for the commodity.
    2. Serialises a concise ``price_snapshot`` JSON.
    3. Builds a prompt describing the farmer's situation and recent prices.
    4. Calls the LLM and records the recommendation.
    """
    advisory = AdvisoryRequest.objects.select_for_update().get(id=request_id)
    commodity = advisory.commodity
    # Get the most recent price for the farmer's county (fallback to national average?)
    latest_price = (
        MarketPrice.objects.filter(commodity=commodity)
        .order_by("-date")
        .first()
    )
    price_snapshot = {
        "commodity": commodity.code,
        "date": latest_price.date.isoformat() if latest_price else None,
        "wholesale_price": str(latest_price.wholesale_price) if latest_price else None,
        "retail_price": str(latest_price.retail_price) if latest_price else None,
    }
    advisory.price_snapshot = price_snapshot
    prompt = (
        f"You are an agricultural advisor. A farmer harvested {advisory.quantity} kg of "
        f"{commodity.name} on {advisory.harvest_date.isoformat()}. The current market "
        f"prices are: wholesale {price_snapshot['wholesale_price']} KES/kg, retail "
        f"{price_snapshot['retail_price']} KES/kg. Advise whether the farmer should "
        f"sell immediately or store the produce for later, providing a brief rationale."
    )
    recommendation = _call_ai(prompt)
    advisory.recommendation = recommendation.strip()
    advisory.save()
    return advisory

# End of services.py
