"""Toolsets definitions, Gemini tool schemas, and execution dispatcher."""

from __future__ import annotations

from typing import Any, Callable, Dict, List
from . import tools

# Mapping tool names to executable python functions
TOOL_REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {
    # FMS Read
    "get_farmer_profile": tools.get_farmer_profile,
    "list_farms": tools.list_farms,
    "list_crops": tools.list_crops,
    "list_recent_harvests": tools.list_recent_harvests,
    "list_open_disease_reports": tools.list_open_disease_reports,
    "get_market_price": tools.get_market_price,
    "get_weather_history": tools.get_weather_history,
    # FMS Write
    "add_farm": tools.add_farm,
    "add_crop": tools.add_crop,
    "log_planting": tools.log_planting,
    "log_input": tools.log_input,
    "log_harvest": tools.log_harvest,
    "record_disease": tools.record_disease,
    "request_advisory": tools.request_advisory,
    # POS Read
    "list_recent_sales": tools.list_recent_sales,
    "list_low_stock_products": tools.list_low_stock_products,
    "list_customers": tools.list_customers,
    "list_recent_purchases": tools.list_recent_purchases,
    # POS Write
    "record_sale": tools.record_sale,
    "record_purchase": tools.record_purchase,
    "update_inventory": tools.update_inventory,
}

# Gemini Function Calling Declarations for FMS
FMS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_farmer_profile",
        "description": "Retrieve the authenticated farmer's profile, location, and farm count.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_farms",
        "description": "List all registered farms belonging to the farmer.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_crops",
        "description": "List crops planted across the farmer's fields.",
        "parameters": {
            "type": "object",
            "properties": {
                "farm_id": {"type": "integer", "description": "Optional specific farm ID"},
            },
        },
    },
    {
        "name": "list_recent_harvests",
        "description": "List recent harvest logs recorded by the farmer.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max entries to return, default 5"},
            },
        },
    },
    {
        "name": "list_open_disease_reports",
        "description": "List unresolved crop diseases and pest issues reported on the farm.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_market_price",
        "description": "Lookup current wholesale and retail prices for an agricultural commodity in a given county.",
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {"type": "string", "description": "Commodity name (e.g. Maize, Beans, Tomatoes)"},
                "county": {"type": "string", "description": "Kenyan county (e.g. Nairobi, Nakuru, Kiambu)"},
            },
            "required": ["commodity"],
        },
    },
    {
        "name": "get_weather_history",
        "description": "Retrieve recent weather measurements (rainfall, temperature) recorded on the farm.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of days"},
            },
        },
    },
    # Write Tools
    {
        "name": "add_farm",
        "description": "Register a new parcel of farm land. Only call after farmer has confirmed details.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name or location of the parcel"},
                "location": {"type": "string", "description": "Village or sub-county"},
                "size": {"type": "number", "description": "Size in acres"},
                "size_unit": {"type": "string", "enum": ["acres", "hectares"]},
                "confirm": {"type": "boolean", "description": "Must be True to save"},
            },
            "required": ["name", "size", "confirm"],
        },
    },
    {
        "name": "add_crop",
        "description": "Add a new crop type to a farm. Only call after confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "description": "Crop name"},
                "variety": {"type": "string", "description": "Seed variety"},
                "area": {"type": "number", "description": "Area allocated in acres"},
                "confirm": {"type": "boolean"},
            },
            "required": ["crop", "confirm"],
        },
    },
    {
        "name": "log_planting",
        "description": "Log planting activity on the farm. Only call after farmer confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "description": "Planted crop name"},
                "area_planted": {"type": "number", "description": "Acres planted"},
                "date": {"type": "string", "format": "date", "description": "YYYY-MM-DD"},
                "cost": {"type": "number", "description": "Total labor/seed cost in KES"},
                "confirm": {"type": "boolean"},
            },
            "required": ["crop", "area_planted", "confirm"],
        },
    },
    {
        "name": "log_input",
        "description": "Record farm inputs applied such as fertilizer, manure, or pesticides. Only call after confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Input name (e.g. DAP, CAN, Urea)"},
                "input_type": {"type": "string", "enum": ["fertilizer", "seed", "pesticide", "manure"]},
                "quantity": {"type": "string", "description": "e.g. 2 bags, 50kg, 10 litres"},
                "cost": {"type": "number", "description": "Cost in KES"},
                "confirm": {"type": "boolean"},
            },
            "required": ["name", "confirm"],
        },
    },
    {
        "name": "log_harvest",
        "description": "Log harvested produce quantities. Only call after confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "description": "Harvested crop"},
                "quantity": {"type": "number", "description": "Amount harvested"},
                "unit": {"type": "string", "enum": ["bag", "kg", "ton", "crate", "piece"]},
                "confirm": {"type": "boolean"},
            },
            "required": ["crop", "quantity", "confirm"],
        },
    },
    {
        "name": "record_disease",
        "description": "Record a plant disease or pest observation. Only call after confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "description": "Affected crop"},
                "symptoms": {"type": "string", "description": "Observed symptoms or damage"},
                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                "confirm": {"type": "boolean"},
            },
            "required": ["crop", "symptoms", "confirm"],
        },
    },
    {
        "name": "request_advisory",
        "description": "Submit a technical question to extension officers. Only call after confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "message": {"type": "string"},
                "confirm": {"type": "boolean"},
            },
            "required": ["subject", "message", "confirm"],
        },
    },
]

# Gemini Function Calling Declarations for POS
POS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "list_recent_sales",
        "description": "List recent sales recorded in the Point of Sale system.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max entries, default 10"},
            },
        },
    },
    {
        "name": "list_low_stock_products",
        "description": "List products in the store with low inventory stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "threshold": {"type": "integer", "description": "Units threshold, default 10"},
            },
        },
    },
    {
        "name": "list_customers",
        "description": "List frequent customers from the sales ledger.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_recent_purchases",
        "description": "List recent store purchases and inventory supplies.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
            },
        },
    },
    # Write Tools
    {
        "name": "record_sale",
        "description": "Record a completed sale in the POS. Only call after the farmer has confirmed the details.",
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "Product sold (e.g. Maize, Beans, Milk)"},
                "quantity": {"type": "number", "description": "Quantity sold"},
                "unit": {"type": "string", "enum": ["bag", "kg", "ton", "litre", "piece"]},
                "price": {"type": "number", "description": "Price per unit in KES"},
                "amount": {"type": "number", "description": "Total amount in KES"},
                "customer": {"type": "string", "description": "Customer name"},
                "payment_method": {"type": "string", "enum": ["cash", "mpesa", "card", "credit"]},
                "date": {"type": "string", "format": "date"},
                "confirm": {"type": "boolean", "description": "Must be True to save"},
            },
            "required": ["product", "quantity", "price", "confirm"],
        },
    },
    {
        "name": "record_purchase",
        "description": "Record a business purchase or restocking expense. Only call after confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Purchased item name"},
                "quantity": {"type": "number", "description": "Quantity bought"},
                "unit_cost": {"type": "number", "description": "Cost per unit in KES"},
                "unit": {"type": "string", "enum": ["bag", "kg", "ton", "litre", "piece"]},
                "supplier": {"type": "string", "description": "Supplier name"},
                "payment_method": {"type": "string", "enum": ["cash", "mpesa", "credit"]},
                "confirm": {"type": "boolean"},
            },
            "required": ["item_name", "quantity", "unit_cost", "confirm"],
        },
    },
    {
        "name": "update_inventory",
        "description": "Update available stock balance in the warehouse or store. Only call after confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Product or item name"},
                "quantity": {"type": "number", "description": "New quantity count"},
                "unit": {"type": "string", "enum": ["bag", "kg", "ton", "litre", "piece"]},
                "confirm": {"type": "boolean"},
            },
            "required": ["item_name", "quantity", "confirm"],
        },
    },
]

GENERAL_TOOLS: List[Dict[str, Any]] = FMS_TOOLS + POS_TOOLS


def execute_tool(user, tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered tool by name with safe exception handling."""
    name = tool_call.get("name")
    args = tool_call.get("args") or {}

    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {
            "ok": False,
            "wrote": False,
            "error": f"Tool '{name}' is not registered.",
            "summary_en": f"Unknown action '{name}'.",
            "sms_text_local": None,
        }

    try:
        return fn(user, **args)
    except Exception as exc:
        return {
            "ok": False,
            "wrote": False,
            "error": str(exc),
            "summary_en": f"Failed to execute {name}: {exc}",
            "sms_text_local": None,
        }
