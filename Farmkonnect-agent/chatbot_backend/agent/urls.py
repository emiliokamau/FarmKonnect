from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AgentActionViewSet,
    AgentAudioRespondView,
    AgentHealthView,
    AgentRespondView,
    ConversationViewSet,
    CropRecordViewSet,
    DiseaseReportViewSet,
    FarmerDataView,
    FarmerContextView,
    FarmViewSet,
    FarmerViewSet,
    HarvestViewSet,
    InventoryViewSet,
    PlantingActivityViewSet,
    SaleViewSet,
)

router = DefaultRouter()
router.register("farmers", FarmerViewSet)
router.register("farms", FarmViewSet)
router.register("crops", CropRecordViewSet)
router.register("planting-activities", PlantingActivityViewSet)
router.register("disease-reports", DiseaseReportViewSet)
router.register("harvests", HarvestViewSet)
router.register("inventory", InventoryViewSet)
router.register("sales", SaleViewSet)
router.register("conversations", ConversationViewSet)
router.register("agent-actions", AgentActionViewSet)

urlpatterns = [
    path("agent/health/", AgentHealthView.as_view(), name="agent-health"),
    path("agent/respond/", AgentRespondView.as_view(), name="agent-respond"),
    path("agent/respond-audio/", AgentAudioRespondView.as_view(), name="agent-audio-respond"),
    path("farmers/<uuid:farmer_id>/context/", FarmerContextView.as_view(), name="farmer-context"),
    path("farmers/<uuid:farmer_id>/data/", FarmerDataView.as_view(), name="farmer-data"),
]
urlpatterns += router.urls
