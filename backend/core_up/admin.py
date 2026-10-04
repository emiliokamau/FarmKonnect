from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, County, Commodity, MarketPrice, Event, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
    FarmerProfile, Farm, CropRecord, PlantingActivity, FarmInput,
    DiseaseReport, Harvest, InventoryItem, Sale, Purchase,
    WeatherLog, ExtensionVisit, FarmFinance,
)


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
    list_display = ("crop", "variety", "farm", "planting_date", "expected_harvest", "area", "area_unit")
    list_filter = ("crop",)


@admin.register(PlantingActivity)
class PlantingActivityAdmin(admin.ModelAdmin):
    list_display = ("date", "crop", "farm", "area_planted", "planting_method")
    list_filter = ("crop",)


@admin.register(FarmInput)
class FarmInputAdmin(admin.ModelAdmin):
    list_display = ("name", "input_type", "farm", "quantity", "cost", "application_date")
    list_filter = ("input_type",)


@admin.register(DiseaseReport)
class DiseaseReportAdmin(admin.ModelAdmin):
    list_display = ("date", "crop", "diagnosis", "severity", "status")
    list_filter = ("severity", "status", "crop")


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
    list_display = ("date", "officer", "farmer", "follow_up_date")


@admin.register(FarmFinance)
class FarmFinanceAdmin(admin.ModelAdmin):
    list_display = ("date", "farmer", "income", "expenses", "loans", "insurance", "subsidies")


# Register the simple ones with default admin
for model in (County, Commodity, MarketPrice, Event, AdvisoryRequest, Product, Listing, Order, DeviceToken):
    if not admin.site.is_registered(model):
        admin.site.register(model)