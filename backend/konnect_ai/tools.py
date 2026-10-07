"""Owner-scoped database tools for Farm Management (FMS) and Point of Sale (POS)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from core_up.models import (
    FarmerProfile,
    Farm,
    CropRecord,
    PlantingActivity,
    FarmInput,
    DiseaseReport,
    Harvest,
    InventoryItem,
    Sale,
    Purchase,
    WeatherLog,
    Commodity,
    County,
    MarketPrice,
    Product,
    AdvisoryRequest,
)


def _get_farmer(user) -> Optional[FarmerProfile]:
    """Retrieve FarmerProfile for user, creating a fallback profile if not found."""
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, "farmer_profile", None)
    if not profile:
        profile, _ = FarmerProfile.objects.get_or_create(
            user=user,
            defaults={"full_name": user.get_full_name() or user.username or "Farmer"},
        )
    return profile


def _get_default_farm(farmer: FarmerProfile) -> Farm:
    """Retrieve farmer's primary farm or create default."""
    farm = Farm.objects.filter(farmer=farmer).first()
    if not farm:
        farm = Farm.objects.create(
            farmer=farmer,
            name=f"{farmer.full_name}'s Farm",
            size=Decimal("2.0"),
            size_unit="acres",
        )
    return farm


# =====================================================================
# FMS READ TOOLS
# =====================================================================

def get_farmer_profile(user, **kwargs) -> Dict[str, Any]:
    """Retrieve farmer profile information."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "error": "User has no farmer profile.", "summary_en": "Profile not found."}
    data = {
        "farmer_id": farmer.farmer_id,
        "full_name": farmer.full_name,
        "county": farmer.county or "N/A",
        "phone": farmer.user.phone or "N/A",
        "preferred_language": farmer.preferred_language,
        "farms_count": farmer.farms.count(),
    }
    return {
        "ok": True,
        "wrote": False,
        "data": data,
        "summary_en": f"Farmer {farmer.full_name} ({farmer.county}) has {data['farms_count']} registered farm(s).",
    }


def list_farms(user, **kwargs) -> Dict[str, Any]:
    """List all registered farms belonging to the farmer."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "error": "No profile.", "summary_en": "No farms found."}
    farms = list(Farm.objects.filter(farmer=farmer).values("id", "name", "location", "size", "size_unit"))
    return {
        "ok": True,
        "wrote": False,
        "data": farms,
        "summary_en": f"Found {len(farms)} farm(s).",
    }


def list_crops(user, farm_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """List active crop records."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "summary_en": "No crops found."}
    qs = CropRecord.objects.filter(farm__farmer=farmer)
    if farm_id:
        qs = qs.filter(farm_id=farm_id)
    crops = list(qs.values("id", "farm__name", "crop", "variety", "area", "area_unit", "planting_date"))
    return {
        "ok": True,
        "wrote": False,
        "data": crops,
        "summary_en": f"Found {len(crops)} crop record(s).",
    }


def list_recent_harvests(user, limit: int = 5, **kwargs) -> Dict[str, Any]:
    """List recent harvests recorded by the farmer."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "summary_en": "No harvests found."}
    harvests = list(
        Harvest.objects.filter(farm__farmer=farmer).order_by("-harvest_date")[:limit].values(
            "id", "crop", "quantity", "unit", "harvest_date", "storage_location"
        )
    )
    return {
        "ok": True,
        "wrote": False,
        "data": harvests,
        "summary_en": f"Found {len(harvests)} recent harvest(s).",
    }


def list_open_disease_reports(user, **kwargs) -> Dict[str, Any]:
    """List unresolved disease reports on the farmer's land."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "summary_en": "No disease reports."}
    reports = list(
        DiseaseReport.objects.filter(farm__farmer=farmer, status__in=["open", "treated"]).values(
            "id", "crop", "symptoms", "diagnosis", "severity", "status", "date"
        )
    )
    return {
        "ok": True,
        "wrote": False,
        "data": reports,
        "summary_en": f"Found {len(reports)} active disease report(s).",
    }


def get_market_price(commodity: str, county: str = "Nairobi", **kwargs) -> Dict[str, Any]:
    """Look up official commodity market price."""
    prices_qs = MarketPrice.objects.filter(
        commodity__name__icontains=commodity,
        county__name__icontains=county,
    ).order_by("-date")

    price_obj = prices_qs.first()
    if not price_obj:
        # Fallback to any county
        price_obj = MarketPrice.objects.filter(commodity__name__icontains=commodity).order_by("-date").first()

    if price_obj:
        data = {
            "commodity": price_obj.commodity.name,
            "county": price_obj.county.name,
            "price": float(price_obj.price),
            "unit": price_obj.commodity.unit,
            "date": str(price_obj.date),
        }
        return {
            "ok": True,
            "wrote": False,
            "data": data,
            "summary_en": f"Market price for {data['commodity']} in {data['county']} is KES {data['price']} per {data['unit']}.",
        }

    return {
        "ok": False,
        "wrote": False,
        "data": None,
        "summary_en": f"No recorded market price was found for {commodity} in {county}.",
    }


def get_weather_history(user, limit: int = 5, **kwargs) -> Dict[str, Any]:
    """Retrieve recent recorded weather measurements."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "summary_en": "No weather data."}
    logs = list(
        WeatherLog.objects.filter(farm__farmer=farmer).order_by("-date")[:limit].values(
            "date", "temperature", "rainfall_mm", "humidity", "notes"
        )
    )
    return {
        "ok": True,
        "wrote": False,
        "data": logs,
        "summary_en": f"Found {len(logs)} weather observation(s).",
    }


# =====================================================================
# FMS WRITE TOOLS (Requires confirm=True)
# =====================================================================

def add_farm(
    user,
    name: str,
    location: str = "",
    size: float = 1.0,
    size_unit: str = "acres",
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Register a new farm for the farmer."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required to add farm '{name}' ({size} {size_unit}).",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    with transaction.atomic():
        farm = Farm.objects.create(
            farmer=farmer,
            name=name,
            location=location,
            size=Decimal(str(size)),
            size_unit=size_unit,
        )

    summary = f"Added farm '{farm.name}' ({farm.size} {farm.size_unit}) successfully."
    sms_text = f"FarmKonnect: Shamba jipya '{farm.name}' la ukubwa wa {farm.size} {farm.size_unit} limerekodiwa."
    return {
        "ok": True,
        "wrote": True,
        "data": {"farm_id": farm.id, "name": farm.name},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def add_crop(
    user,
    crop: str,
    farm_id: Optional[int] = None,
    variety: str = "",
    area: float = 1.0,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Add a new crop record to a farm."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required to record crop '{crop}' ({area} acres).",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    if farm_id:
        farm = Farm.objects.filter(farmer=farmer, id=farm_id).first()
        if not farm:
            return {
                "ok": False,
                "wrote": False,
                "summary_en": f"Farm with ID {farm_id} not found or does not belong to you.",
                "sms_text_local": None,
            }
    else:
        farm = _get_default_farm(farmer)

    with transaction.atomic():
        record = CropRecord.objects.create(
            farm=farm,
            crop=crop,
            variety=variety,
            area=Decimal(str(area)),
            planting_date=datetime.date.today(),
        )

    summary = f"Recorded crop '{crop}' ({variety}) on farm '{farm.name}'."
    sms_text = f"FarmKonnect: Rekodi ya zao la {crop} kwenye shamba la {farm.name} imehifadhiwa."
    return {
        "ok": True,
        "wrote": True,
        "data": {"crop_id": record.id, "crop": record.crop},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def log_planting(
    user,
    crop: str = "Maize",
    area_planted: float = 1.0,
    date: Optional[str] = None,
    cost: float = 0.0,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Log a planting activity."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required: Log planting of {area_planted} acres of {crop}?",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    farm = _get_default_farm(farmer)
    planting_date = datetime.date.fromisoformat(date) if date else datetime.date.today()

    with transaction.atomic():
        crop_record, _ = CropRecord.objects.get_or_create(
            farm=farm,
            crop=crop,
            defaults={"area": Decimal(str(area_planted)), "planting_date": planting_date},
        )
        activity = PlantingActivity.objects.create(
            crop_record=crop_record,
            date=planting_date,
            activity_type="planting",
            description=f"Planted {area_planted} acres of {crop}",
            cost=Decimal(str(cost)),
        )

    summary = f"Logged planting of {area_planted} acres of {crop} on {planting_date}."
    sms_text = f"FarmKonnect: Upanzi wa ekari {area_planted} za {crop} umerekodiwa kwenye shamba la {farm.name}."
    return {
        "ok": True,
        "wrote": True,
        "data": {"planting_id": activity.id, "crop": crop, "date": str(planting_date)},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def log_input(
    user,
    name: str = "DAP Fertilizer",
    input_type: str = "fertilizer",
    quantity: str = "1 bag",
    cost: float = 0.0,
    farm_id: Optional[int] = None,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Log an input (fertilizer, seeds, chemicals) applied to the farm."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required to log input {name} ({quantity}).",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    farm = Farm.objects.filter(farmer=farmer, id=farm_id).first() if farm_id else _get_default_farm(farmer)

    with transaction.atomic():
        item = FarmInput.objects.create(
            farm=farm,
            name=name,
            input_type=input_type,
            quantity=Decimal("1.0"),
            unit=quantity,
            cost=Decimal(str(cost)),
            date_applied=datetime.date.today(),
        )

    summary = f"Recorded input '{name}' ({quantity}) on farm '{farm.name}'."
    sms_text = f"FarmKonnect: Pembejeo ya {name} ({quantity}) imerekodiwa kwa shamba la {farm.name}."
    return {
        "ok": True,
        "wrote": True,
        "data": {"input_id": item.id, "name": item.name},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def log_harvest(
    user,
    crop: str = "Maize",
    quantity: float = 10.0,
    unit: str = "bag",
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Log a crop harvest."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required: Log harvest of {quantity} {unit}s of {crop}?",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    farm = _get_default_farm(farmer)

    with transaction.atomic():
        h = Harvest.objects.create(
            farm=farm,
            crop=crop,
            harvest_date=datetime.date.today(),
            quantity=Decimal(str(quantity)),
            unit=unit,
        )

    summary = f"Logged harvest of {quantity} {unit}(s) of {crop}."
    sms_text = f"FarmKonnect: Mavuno ya {quantity} {unit} za {crop} yamerekodiwa kwa ufanisi."
    return {
        "ok": True,
        "wrote": True,
        "data": {"harvest_id": h.id, "crop": crop, "quantity": float(h.quantity)},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def record_disease(
    user,
    crop: str = "Maize",
    symptoms: str = "brown spots",
    severity: str = "medium",
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Create a disease incident report."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required to record disease on {crop} with symptoms: '{symptoms}'.",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    farm = _get_default_farm(farmer)

    with transaction.atomic():
        report = DiseaseReport.objects.create(
            farm=farm,
            date=datetime.date.today(),
            crop=crop,
            symptoms=symptoms,
            severity=severity if severity in ("low", "medium", "high") else "medium",
            status="open",
        )

    summary = f"Recorded disease report for {crop} ({symptoms}). Status: Open."
    sms_text = f"FarmKonnect: Ripoti ya ugonjwa wa {crop} imetumwa. Afisa ugani atawasiliana nawe."
    return {
        "ok": True,
        "wrote": True,
        "data": {"report_id": report.id, "crop": crop},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def request_advisory(
    user,
    subject: str,
    message: str,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Submit a question or advisory request to extension officers."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required to send advisory message: '{subject}'.",
            "sms_text_local": None,
        }

    with transaction.atomic():
        adv = AdvisoryRequest.objects.create(
            user=user,
            subject=subject,
            message=message,
            status="open",
        )

    summary = f"Advisory request '{subject}' submitted to agricultural officers."
    sms_text = f"FarmKonnect: Ombi lako la ushauri '{subject}' limepokelewa na maofisa wa kilimo."
    return {
        "ok": True,
        "wrote": True,
        "data": {"advisory_id": adv.id, "subject": adv.subject},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


# =====================================================================
# POS READ TOOLS
# =====================================================================

def list_recent_sales(user, limit: int = 10, **kwargs) -> Dict[str, Any]:
    """List recent product sales in the POS."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "summary_en": "No sales found."}
    sales = list(
        Sale.objects.filter(farmer=farmer).order_by("-date")[:limit].values(
            "id", "product", "quantity", "unit", "price", "amount", "customer", "date"
        )
    )
    return {
        "ok": True,
        "wrote": False,
        "data": sales,
        "summary_en": f"Found {len(sales)} recent sale(s).",
    }


def list_low_stock_products(user, threshold: int = 10, **kwargs) -> Dict[str, Any]:
    """List products that are running low on stock."""
    products = list(
        Product.objects.filter(is_active=True, stock__lte=threshold).values("id", "name", "price", "stock", "category")
    )
    return {
        "ok": True,
        "wrote": False,
        "data": products,
        "summary_en": f"Found {len(products)} low-stock product(s).",
    }


def list_customers(user, **kwargs) -> Dict[str, Any]:
    """List known customers derived from the farmer's sales history."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "summary_en": "No customers found."}
    customers = list(
        Sale.objects.filter(farmer=farmer)
        .exclude(customer="")
        .values("customer")
        .distinct()[:20]
    )
    return {
        "ok": True,
        "wrote": False,
        "data": customers,
        "summary_en": f"Found {len(customers)} customer(s).",
    }


def list_recent_purchases(user, limit: int = 10, **kwargs) -> Dict[str, Any]:
    """List recent purchases or store inventory acquisitions."""
    farmer = _get_farmer(user)
    if not farmer:
        return {"ok": False, "wrote": False, "summary_en": "No purchases found."}
    purchases = list(
        Purchase.objects.filter(farmer=farmer).order_by("-purchase_date")[:limit].values(
            "id", "item", "quantity", "supplier", "cost", "purchase_date", "notes"
        )
    )
    return {
        "ok": True,
        "wrote": False,
        "data": purchases,
        "summary_en": f"Found {len(purchases)} recent purchase(s).",
    }


# =====================================================================
# POS WRITE TOOLS (Requires confirm=True)
# =====================================================================

def record_sale(
    user,
    product: str,
    quantity: float,
    price: float,
    unit: str = "bag",
    amount: Optional[float] = None,
    customer: str = "Walk-in Customer",
    payment_method: str = "cash",
    date: Optional[str] = None,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Record a product sale in the POS with atomic consistency."""
    total = amount if amount is not None else float(quantity) * float(price)
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required: Record sale of {quantity} {unit}(s) of {product} at KES {price} each (Total: KES {total})?",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    sale_date = datetime.date.fromisoformat(date) if date else datetime.date.today()

    with transaction.atomic():
        sale = Sale.objects.create(
            farmer=farmer,
            customer=customer or "Walk-in Customer",
            product=product,
            quantity=Decimal(str(quantity)),
            unit=unit,
            price=Decimal(str(price)),
            amount=Decimal(str(total)),
            payment_method=payment_method if payment_method in ("cash", "mpesa", "card", "credit") else "cash",
            date=sale_date,
        )

        # Automatically decrement matching product stock if present
        prod = Product.objects.filter(name__icontains=product).first()
        if prod and prod.stock >= quantity:
            prod.stock -= int(quantity)
            prod.save(update_fields=["stock"])

    summary = f"Recorded sale of {quantity} {unit}(s) of {product} for KES {total:g}."
    sms_text = f"FarmKonnect POS: Mauzo ya {quantity} {unit} za {product} kwa KES {total:g} yamerekodiwa kwa mteja {customer}."
    return {
        "ok": True,
        "wrote": True,
        "data": {"sale_id": sale.id, "product": product, "total": total},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def record_purchase(
    user,
    item_name: str,
    quantity: float,
    unit_cost: float,
    unit: str = "bag",
    supplier: str = "",
    payment_method: str = "cash",
    date: Optional[str] = None,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Record a stock purchase or inventory expenditure."""
    total = float(quantity) * float(unit_cost)
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required: Record purchase of {quantity} {unit}(s) of {item_name} at KES {unit_cost} (Total KES {total})?",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    p_date = datetime.date.fromisoformat(date) if date else datetime.date.today()

    with transaction.atomic():
        purchase = Purchase.objects.create(
            farmer=farmer,
            supplier=supplier or "Local Supplier",
            item=item_name,
            quantity=f"{quantity} {unit}",
            cost=Decimal(str(total)),
            purchase_date=p_date,
        )

    summary = f"Recorded purchase of {quantity} {unit}(s) of {item_name} for KES {total:g}."
    sms_text = f"FarmKonnect POS: Ununuzi wa {quantity} {unit} za {item_name} kwa KES {total:g} umerekodiwa."
    return {
        "ok": True,
        "wrote": True,
        "data": {"purchase_id": purchase.id, "item_name": item_name, "total": total},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }


def update_inventory(
    user,
    item_name: str,
    quantity: float,
    unit: str = "bag",
    farm_id: Optional[int] = None,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Update stock quantity in farm inventory."""
    if not confirm:
        return {
            "ok": False,
            "wrote": False,
            "summary_en": f"Confirmation required to update inventory for '{item_name}' to {quantity} {unit}s.",
            "sms_text_local": None,
        }

    farmer = _get_farmer(user)
    farm = Farm.objects.filter(farmer=farmer, id=farm_id).first() if farm_id else _get_default_farm(farmer)

    with transaction.atomic():
        item, created = InventoryItem.objects.get_or_create(
            farm=farm,
            item_name=item_name,
            defaults={"quantity": Decimal(str(quantity)), "unit": unit},
        )
        if not created:
            item.quantity = Decimal(str(quantity))
            item.unit = unit
            item.save(update_fields=["quantity", "unit"])

    summary = f"Updated inventory for '{item_name}' to {quantity} {unit}(s)."
    sms_text = f"FarmKonnect: Idadi ya bidhaa '{item_name}' stooni imesasishwa kuwa {quantity} {unit}."
    return {
        "ok": True,
        "wrote": True,
        "data": {"item_id": item.id, "item_name": item.item_name, "quantity": float(item.quantity)},
        "summary_en": summary,
        "sms_text_local": sms_text,
    }
