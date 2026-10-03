from rest_framework import serializers

from .models import (
    AgentAction,
    Conversation,
    CropRecord,
    DiseaseReport,
    Farm,
    Farmer,
    Harvest,
    Inventory,
    PlantingActivity,
    Sale,
)


class FarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = "__all__"
        read_only_fields = ["farmer_id", "created_at"]


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = "__all__"
        read_only_fields = ["farm_id", "created_at"]


class CropRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropRecord
        fields = "__all__"
        read_only_fields = ["crop_record_id", "created_at"]


class PlantingActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantingActivity
        fields = "__all__"
        read_only_fields = ["activity_id", "created_at"]


class DiseaseReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiseaseReport
        fields = "__all__"
        read_only_fields = ["report_id", "reported_at"]


class HarvestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Harvest
        fields = "__all__"
        read_only_fields = ["harvest_id", "created_at"]


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = "__all__"
        read_only_fields = ["inventory_id", "last_updated"]


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = "__all__"
        read_only_fields = ["sale_id", "sale_date"]


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = "__all__"
        read_only_fields = ["conversation_id", "created_at", "ai_response"]


class AgentActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentAction
        fields = "__all__"
        read_only_fields = ["action_id", "created_at"]


class AgentRequestSerializer(serializers.Serializer):
    farmer_id = serializers.UUIDField()
    message = serializers.CharField()


class AudioAgentRequestSerializer(serializers.Serializer):
    farmer_id = serializers.UUIDField()
    audio = serializers.FileField()


class AgentResponseSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    farmer_id = serializers.UUIDField()
    intent = serializers.CharField()
    context = serializers.JSONField()
    response = serializers.CharField()


class AudioAgentResponseSerializer(AgentResponseSerializer):
    transcript = serializers.CharField()
    translation = serializers.CharField()
    audio_base64 = serializers.CharField()
    audio_content_type = serializers.CharField()
