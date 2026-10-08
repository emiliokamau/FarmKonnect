"""DRF serializers for KonnectAI sessions and dialogue turns."""

from rest_framework import serializers
from .models import ConversationSession, AuditLog


class ConversationSessionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ConversationSession
        fields = [
            "id",
            "username",
            "started_at",
            "ended_at",
            "language",
            "modality",
            "transcript",
            "tool_calls",
            "sms_sent",
        ]
        read_only_fields = ["id", "started_at", "ended_at", "transcript", "tool_calls", "sms_sent"]


class TurnRequestSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(required=False, allow_null=True)
    text = serializers.CharField(max_length=2000, required=True)
    language = serializers.ChoiceField(choices=["auto", "sw", "en"], default="auto")
    page = serializers.ChoiceField(choices=["dashboard", "pos", "farmer", "home"], default="dashboard")


class TurnResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    reply_en = serializers.CharField()
    intent = serializers.CharField()
    tool_calls = serializers.ListField(child=serializers.DictField(), default=list)
    sms_sent = serializers.BooleanField(default=False)
    session_id = serializers.IntegerField()


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "username",
            "session",
            "intent",
            "tool_name",
            "args",
            "ok",
            "result",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
