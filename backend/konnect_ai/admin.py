from django.contrib import admin
from .models import ConversationSession, AuditLog


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "language", "modality", "sms_sent", "started_at", "ended_at")
    list_filter = ("language", "modality", "sms_sent", "started_at")
    search_fields = ("user__username", "user__phone", "user__email")
    readonly_fields = ("started_at", "ended_at", "transcript", "tool_calls")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "intent", "tool_name", "ok", "created_at")
    list_filter = ("intent", "ok", "created_at")
    search_fields = ("user__username", "user__phone", "tool_name")
    readonly_fields = ("created_at", "args", "result")
