from django.contrib import admin

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

for model in [Farmer, Farm, CropRecord, PlantingActivity, DiseaseReport, Harvest, Inventory, Sale, Conversation, AgentAction]:
    admin.site.register(model)
