from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User, County, Commodity, MarketPrice, Event, EventRegistration, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
    FarmerProfile, Farm, CropRecord, PlantingActivity, FarmInput,
    DiseaseReport, DiseasePhoto, Harvest, InventoryItem, Sale, Purchase,
    WeatherLog, ExtensionVisit, FarmFinance,
)


def thumbnail(obj, field="image", height=60):
    """Small preview of an uploaded photo, or a dash when there is none."""
    src = obj.image_src if field == "image" else getattr(getattr(obj, field, None), "url", "")
    if not src:
        return "—"
    return format_html(
        '<a href="{0}" target="_blank">'
        '<img src="{0}" style="height:{1}px;border-radius:6px;border:1px solid #e5e7eb;" />'
        "</a>",
        src, height,
    )


thumbnail.short_description = "Photo"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "phone", "is_staff", "is_phone_verified", "profile_completed")
    search_fields = ("username", "email", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("FarmKonnect", {"fields": ("phone", "is_phone_verified", "otp_code", "otp_created_at", "profile_completed")}),
    )


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ("farmer_id", "full_name", "user", "county", "sub_county", "preferred_language")
    search_fields = ("farmer_id", "full_name", "user__username", "county")
    list_filter = ("preferred_language", "county")


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("name", "farmer", "size", "size_unit", "soil_type", "ownership_type", "irrigation_available")
    list_filter = ("soil_type", "ownership_type", "irrigation_available")
    search_fields = ("name", "farmer__full_name")


@admin.register(CropRecord)
class CropRecordAdmin(admin.ModelAdmin):
    list_display = ("crop", "variety", "farm", "planting_date", "expected_harvest", "area", "area_unit", "photo")
    list_filter = ("crop",)
    search_fields = ("crop", "variety", "farm__name")
    fieldsets = (
        ("Crop", {"fields": ("farm", "crop", "variety", "seed_source")}),
        ("Dates & area", {"fields": ("planting_date", "expected_harvest", "area", "area_unit")}),
        ("Photos", {"fields": ("image", "photo_url"),
                    "description": "Upload a field photo, or paste a link if the image is hosted elsewhere."}),
        ("Notes", {"fields": ("notes",)}),
    )

    @admin.display(description="Photo")
    def photo(self, obj):
        return thumbnail(obj)


@admin.register(PlantingActivity)
class PlantingActivityAdmin(admin.ModelAdmin):
    list_display = ("date", "crop", "farm", "area_planted", "planting_method")
    list_filter = ("crop",)


@admin.register(FarmInput)
class FarmInputAdmin(admin.ModelAdmin):
    list_display = ("name", "input_type", "farm", "farmer", "quantity", "cost", "application_date")
    list_filter = ("input_type",)
    search_fields = (
        "name",
        "crop",
        "farm__name",
        "farm__farmer__farmer_id",
        "farm__farmer__full_name",
        "farm__farmer__user__username",
        "farm__farmer__user__email",
        "farm__farmer__user__phone",
    )
    list_select_related = ("farm", "farm__farmer", "farm__farmer__user")

    @admin.display(description="Farmer", ordering="farm__farmer__full_name")
    def farmer(self, obj):
        profile = obj.farm.farmer
        return f"{profile.full_name} ({profile.farmer_id})"


class DiseasePhotoInline(admin.TabularInline):
    model = DiseasePhoto
    extra = 0
    fields = ("image", "photo_stage", "caption", "preview")
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self, obj):
        return thumbnail(obj, field="image")


@admin.register(DiseaseReport)
class DiseaseReportAdmin(admin.ModelAdmin):
    list_display = ("date", "crop", "diagnosis", "severity", "status", "photo", "needs_analysis")
    list_filter = ("severity", "status", "crop", "needs_analysis", "photo_stage")
    search_fields = ("crop", "variety", "diagnosis", "symptoms", "farm__name")
    inlines = [DiseasePhotoInline]
    fieldsets = (
        ("Crop", {"fields": ("farm", "crop", "variety", "growth_stage", "date")}),
        ("What the farmer reported", {"fields": ("symptoms", "affected_area")}),
        ("Photos", {"fields": ("image", "photo_stage", "photo_url"),
                    "description": "The main photo. Add further angles in the section below."}),
        ("Assessment", {"fields": ("diagnosis", "needs_analysis", "severity", "treatment", "status")}),
    )

    @admin.display(description="Photo")
    def photo(self, obj):
        return thumbnail(obj)


@admin.register(DiseasePhoto)
class DiseasePhotoAdmin(admin.ModelAdmin):
    list_display = ("report", "photo_stage", "caption", "preview", "created_at")
    list_filter = ("photo_stage",)
    search_fields = ("report__crop", "caption")

    @admin.display(description="Preview")
    def preview(self, obj):
        return thumbnail(obj, field="image")


@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):
    list_display = ("crop", "harvest_date", "quantity", "unit", "grade", "storage_facility")
    list_filter = ("crop", "grade")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "unit", "farm", "storage_location", "updated_at")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("date", "product", "quantity", "unit", "amount", "customer", "payment_method")
    list_filter = ("payment_method",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("purchase_date", "item", "quantity", "cost", "supplier")
    list_filter = ("supplier",)


@admin.register(WeatherLog)
class WeatherLogAdmin(admin.ModelAdmin):
    list_display = ("date", "farm", "rainfall_mm", "temperature_c", "humidity_pct")


@admin.register(ExtensionVisit)
class ExtensionVisitAdmin(admin.ModelAdmin):
    list_display = ("date", "officer", "farmer_name", "follow_up_date")
    list_filter = ("follow_up_date",)
    search_fields = (
        "officer",
        "recommendations",
        "farmer__farmer_id",
        "farmer__full_name",
        "farmer__user__username",
        "farmer__user__email",
        "farmer__user__phone",
    )
    list_select_related = ("farmer", "farmer__user")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["farmer"].required = True
        form.base_fields["farmer"].help_text = (
            "Required: the assigned farmer receives this visit in Extension Visits."
        )
        return form

    @admin.display(description="Farmer", ordering="farmer__full_name")
    def farmer_name(self, obj):
        if obj.farmer is None:
            return "Unassigned"
        return f"{obj.farmer.full_name} ({obj.farmer.farmer_id})"


@admin.register(FarmFinance)
class FarmFinanceAdmin(admin.ModelAdmin):
    list_display = ("date", "farmer", "income", "expenses", "loans", "insurance", "subsidies")


class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "scope", "event_type", "join_mode", "start_date", "is_online", "cost", "is_active")
    list_filter = ("scope", "event_type", "join_mode", "cost", "is_online", "is_active", "country")
    search_fields = ("title", "host", "location", "region", "country", "tags")
    date_hierarchy = "start_date"
    fieldsets = (
        ("Event", {"fields": ("title", "description", "host", "event_type", "image_url", "tags")}),
        ("When & where", {"fields": ("start_date", "end_date", "scope", "country", "region", "location", "is_online")}),
        ("How farmers join", {
            "fields": ("join_mode", "join_url", "whatsapp_link", "access_link", "access_code"),
            "description": "Paste the host's Google Meet / Zoom / livestream link. Farmers see the Join button automatically.",
        }),
        ("Registration", {
            "fields": ("registration_required", "registration_url", "registration_deadline", "capacity", "cost")
        }),
        ("Publishing", {"fields": ("source_url", "is_active")}),
    )


class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "event", "phone", "county", "status", "reference", "created_at")
    list_filter = ("status", "wants_reminder", "event__scope")
    search_fields = ("full_name", "phone", "email", "reference", "event__title")
    readonly_fields = ("reference", "created_at")


# Register the simple ones with default admin
for model in (County, Commodity, MarketPrice, AdvisoryRequest, Product, Listing, Order, DeviceToken):
    if not admin.site.is_registered(model):
        admin.site.register(model)

if not admin.site.is_registered(Event):
    admin.site.register(Event, EventAdmin)

if not admin.site.is_registered(EventRegistration):
    admin.site.register(EventRegistration, EventRegistrationAdmin)