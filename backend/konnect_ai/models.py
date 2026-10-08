from django.conf import settings
from django.db import models


class ConversationSession(models.Model):
    """Stores voice and text conversational sessions with KonnectAI."""
    LANGUAGE_CHOICES = [
        ("auto", "Auto Detect"),
        ("sw", "Kiswahili"),
        ("en", "English"),
    ]
    MODALITY_CHOICES = [
        ("text", "Text"),
        ("voice", "Voice"),
        ("mixed", "Mixed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="auto")
    modality = models.CharField(max_length=10, choices=MODALITY_CHOICES, default="mixed")
    transcript = models.JSONField(default=list, blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    sms_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Conversation Session"
        verbose_name_plural = "Conversation Sessions"

    def __str__(self):
        return f"Session #{self.id} - {self.user} ({self.started_at:%Y-%m-%d %H:%M})"


class AuditLog(models.Model):
    """Immutable audit trail for every AI tool call, parameters, and results."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_audit_logs",
    )
    session = models.ForeignKey(
        ConversationSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    intent = models.CharField(max_length=10)  # FMS | POS | GENERAL
    tool_name = models.CharField(max_length=80)
    args = models.JSONField(default=dict)
    ok = models.BooleanField()
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI Audit Log"
        verbose_name_plural = "AI Audit Logs"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["tool_name", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.intent}] {self.tool_name} by {self.user} (ok={self.ok})"
