from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from django.shortcuts import render

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
from .serializers import (
    AgentActionSerializer,
    AudioAgentRequestSerializer,
    AudioAgentResponseSerializer,
    AgentRequestSerializer,
    AgentResponseSerializer,
    ConversationSerializer,
    CropRecordSerializer,
    DiseaseReportSerializer,
    FarmSerializer,
    FarmerSerializer,
    HarvestSerializer,
    InventorySerializer,
    PlantingActivitySerializer,
    SaleSerializer,
)
from .services import build_farmer_context, build_farmer_data, respond_to_farmer, transcribe_and_translate_audio


class FarmerViewSet(viewsets.ModelViewSet):
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer


class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.all()
    serializer_class = FarmSerializer


class CropRecordViewSet(viewsets.ModelViewSet):
    queryset = CropRecord.objects.all()
    serializer_class = CropRecordSerializer


class PlantingActivityViewSet(viewsets.ModelViewSet):
    queryset = PlantingActivity.objects.all()
    serializer_class = PlantingActivitySerializer


class DiseaseReportViewSet(viewsets.ModelViewSet):
    queryset = DiseaseReport.objects.all()
    serializer_class = DiseaseReportSerializer


class HarvestViewSet(viewsets.ModelViewSet):
    queryset = Harvest.objects.all()
    serializer_class = HarvestSerializer


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer


class AgentActionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgentAction.objects.all()
    serializer_class = AgentActionSerializer


class AgentRespondView(APIView):
    def post(self, request):
        serializer = AgentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            farmer = Farmer.objects.get(farmer_id=serializer.validated_data["farmer_id"])
        except Farmer.DoesNotExist:
            return Response({"detail": "Farmer not found."}, status=status.HTTP_404_NOT_FOUND)
        result = respond_to_farmer(farmer, serializer.validated_data["message"])
        return Response(AgentResponseSerializer(result).data, status=status.HTTP_200_OK)


class AgentAudioRespondView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AudioAgentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            farmer = Farmer.objects.get(farmer_id=serializer.validated_data["farmer_id"])
        except Farmer.DoesNotExist:
            return Response({"detail": "Farmer not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            transcript, translation, audio_base64, audio_content_type = transcribe_and_translate_audio(
                serializer.validated_data["audio"]
            )
        except (RuntimeError, ValueError) as error:
            return Response({"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        result = respond_to_farmer(farmer, translation)
        result["transcript"] = transcript
        result["translation"] = translation
        result["audio_base64"] = audio_base64
        result["audio_content_type"] = audio_content_type
        return Response(AudioAgentResponseSerializer(result).data, status=status.HTTP_200_OK)


class AgentHealthView(APIView):
    def get(self, request):
        return Response({"status": "ok", "service": "farmkonnect-agent"})


def VoiceTestView(request):
    return render(request, "agent/voice_test.html")


class FarmerContextView(APIView):
    def get(self, request, farmer_id):
        try:
            farmer = Farmer.objects.get(farmer_id=farmer_id)
        except Farmer.DoesNotExist:
            return Response({"detail": "Farmer not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_farmer_context(farmer))


class FarmerDataView(APIView):
    def get(self, request, farmer_id):
        try:
            farmer = Farmer.objects.get(farmer_id=farmer_id)
        except Farmer.DoesNotExist:
            return Response({"detail": "Farmer not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_farmer_data(farmer))
