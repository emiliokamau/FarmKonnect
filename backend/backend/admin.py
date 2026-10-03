from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, County, Commodity, MarketPrice, Event, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "phone", "is_staff", "is_phone_verified")
    search_fields = ("username", "email", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("FarmKonnect", {"fields": ("phone", "is_phone_verified", "otp_code", "otp_created_at")}),
    )


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code")
    search_fields = ("name",)


@admin.register(Commodity)
class CommodityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unit", "category")
    search_fields = ("name",)


@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    list_display = ("id", "commodity", "county", "price", "date", "source")
    list_filter = ("commodity", "county", "date")
    search_fields = ("commodity__name", "county__name")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "event_type", "location", "start_date", "is_active")
    list_filter = ("event_type", "is_active")
    search_fields = ("title", "location")


@admin.register(AdvisoryRequest)
class AdvisoryRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("subject", "user__email", "user__phone")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sku", "price", "stock", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "owner", "quantity", "price", "county", "is_active")
    list_filter = ("is_active", "county")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "customer_phone", "total", "status", "created_at")
    list_filter = ("status",)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "platform", "created_at")