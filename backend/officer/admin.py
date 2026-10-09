from django.contrib import admin
from .models import ExtensionOfficer, Appointment

@admin.register(ExtensionOfficer)
class ExtensionOfficerAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "region", "license_number", "verified")
    search_fields = ("user__username", "license_number", "region")
    list_filter = ("verified", "region")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("farmer", "officer", "target_datetime", "status")
    search_fields = ("farmer__username", "officer__user__username", "crop")
    list_filter = ("status", "target_datetime")
    date_hierarchy = "target_datetime"
