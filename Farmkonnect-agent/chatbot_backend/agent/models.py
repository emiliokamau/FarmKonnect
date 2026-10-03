import uuid

from django.db import models


class Farmer(models.Model):
    farmer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, unique=True)
    national_id = models.CharField(max_length=30, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    county = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(max_length=20, default="kiswahili")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class Farm(models.Model):
    farm_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="farms")
    farm_name = models.CharField(max_length=150, blank=True)
    acreage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    soil_type = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    irrigation_available = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class CropRecord(models.Model):
    crop_record_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="crop_records")
    crop_name = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True)
    area_planted = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    planting_date = models.DateField(null=True, blank=True)
    expected_harvest_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default="active")
    created_at = models.DateTimeField(auto_now_add=True)


class PlantingActivity(models.Model):
    activity_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crop_record = models.ForeignKey(CropRecord, on_delete=models.CASCADE, related_name="planting_activities")
    activity_date = models.DateField(null=True, blank=True)
    seed_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    seed_unit = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DiseaseReport(models.Model):
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crop_record = models.ForeignKey(CropRecord, on_delete=models.CASCADE, related_name="disease_reports")
    symptoms = models.TextField()
    probable_disease = models.CharField(max_length=200, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    severity = models.CharField(max_length=50, blank=True)
    treatment_recommendation = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)


class Harvest(models.Model):
    harvest_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crop_record = models.ForeignKey(CropRecord, on_delete=models.CASCADE, related_name="harvests")
    harvest_date = models.DateField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Inventory(models.Model):
    inventory_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="inventory")
    product_name = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)


class Sale(models.Model):
    sale_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="sales")
    product_name = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True)
    sale_date = models.DateTimeField(auto_now_add=True)


class Conversation(models.Model):
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="conversations")
    original_message = models.TextField()
    normalized_message = models.TextField(blank=True)
    language_detected = models.CharField(max_length=30, blank=True)
    intent = models.CharField(max_length=100, blank=True)
    extracted_entities = models.JSONField(default=dict, blank=True)
    ai_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AgentAction(models.Model):
    action_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_actions")
    intent = models.CharField(max_length=100)
    target_module = models.CharField(max_length=100)
    action_taken = models.TextField()
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
