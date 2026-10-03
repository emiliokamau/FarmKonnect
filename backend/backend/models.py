import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


def gen_uuid():
    return uuid.uuid4().hex[:12]


class User(AbstractUser):
    """Custom user with phone-based OTP login."""
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    profile_completed = models.BooleanField(default=False)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "phone"]

    def __str__(self):
        return self.username or self.phone or self.email


# ---------- Reference ----------

class County(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name_plural = "Counties"

    def __str__(self):
        return self.name


class Commodity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=20, default="kg")
    category = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "Commodities"

    def __str__(self):
        return self.name


class MarketPrice(models.Model):
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, related_name="prices")
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name="prices")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    source = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.commodity} - {self.county} - {self.price}"


# ---------- 1. Farmer Profile ----------

class FarmerProfile(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("sw", "Kiswahili"),
        ("ki", "Kikuyu"),
        ("lu", "Luo"),
        ("ka", "Kamba"),
        ("luy", "Luhya"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="farmer_profile")
    farmer_id = models.CharField(max_length=20, unique=True, default=gen_uuid)
    national_id = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    county = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="en")
    farmer_group = models.CharField(max_length=150, blank=True)
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.farmer_id} · {self.full_name}"


# ---------- 2. Farm ----------

class Farm(models.Model):
    SOIL_CHOICES = [
        ("sandy", "Sandy"), ("loam", "Loam"), ("clay", "Clay"),
        ("silt", "Silt"), ("peat", "Peat"), ("chalk", "Chalk"),
    ]
    OWNERSHIP_CHOICES = [
        ("owned", "Owned"), ("leased", "Leased"),
        ("family", "Family Land"), ("communal", "Communal"),
    ]

    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name="farms")
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200, blank=True)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    size = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    size_unit = models.CharField(max_length=10, default="acres")
    soil_type = models.CharField(max_length=20, choices=SOIL_CHOICES, blank=True)
    ownership_type = models.CharField(max_length=20, choices=OWNERSHIP_CHOICES, blank=True)
    water_source = models.CharField(max_length=100, blank=True)
    irrigation_available = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ---------- 3. Crop Records ----------

class CropRecord(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="crops")
    crop = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True)
    planting_date = models.DateField(null=True, blank=True)
    expected_harvest = models.DateField(null=True, blank=True)
    area = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    area_unit = models.CharField(max_length=10, default="acres")
    seed_source = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop} @ {self.farm.name}"


# ---------- 4. Planting Activities ----------

class PlantingActivity(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="plantings")
    date = models.DateField()
    crop = models.CharField(max_length=100)
    seed_variety = models.CharField(max_length=100, blank=True)
    area_planted = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    seed_quantity = models.CharField(max_length=100, blank=True)
    planting_method = models.CharField(max_length=100, blank=True)
    responsible_person = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Planting {self.crop} on {self.date}"


# ---------- 5. Input Usage ----------

class FarmInput(models.Model):
    INPUT_TYPES = [
        ("fertilizer", "Fertilizer"),
        ("pesticide", "Pesticide"),
        ("herbicide", "Herbicide"),
        ("fungicide", "Fungicide"),
        ("seed", "Seed"),
        ("other", "Other"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="inputs")
    name = models.CharField(max_length=150)
    input_type = models.CharField(max_length=20, choices=INPUT_TYPES, default="fertilizer")
    quantity = models.CharField(max_length=100, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    application_date = models.DateField(null=True, blank=True)
    crop = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-application_date"]

    def __str__(self):
        return f"{self.name} ({self.input_type})"


# ---------- 6. Disease & Pest Reports ----------

class DiseaseReport(models.Model):
    SEVERITY = [("low", "Low"), ("medium", "Medium"), ("high", "High")]
    STATUS = [("open", "Open"), ("treated", "Treated"), ("resolved", "Resolved")]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="diseases", null=True, blank=True)
    date = models.DateField()
    crop = models.CharField(max_length=100)
    symptoms = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    diagnosis = models.CharField(max_length=200, blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY, default="low")
    treatment = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.crop} · {self.diagnosis or 'undiagnosed'}"


# ---------- 7. Harvest ----------

class Harvest(models.Model):
    GRADE_CHOICES = [("A", "Grade A"), ("B", "Grade B"), ("C", "Grade C")]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="harvests", null=True, blank=True)
    crop = models.CharField(max_length=100)
    harvest_date = models.DateField()
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="kg")
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    storage_facility = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-harvest_date"]

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.crop}"


# ---------- 8. Inventory ----------

class InventoryItem(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory")
    product = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="kg")
    source_harvest = models.ForeignKey(Harvest, on_delete=models.SET_NULL, null=True, blank=True)
    storage_location = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product} ({self.quantity} {self.unit})"


# ---------- 9. Sales (POS) ----------

class Sale(models.Model):
    PAYMENT_CHOICES = [("cash", "Cash"), ("mpesa", "M-Pesa"), ("card", "Card"), ("credit", "Credit")]

    farmer = models.ForeignKey(FarmerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    date = models.DateField()
    product = models.CharField(max_length=150)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="kg")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    customer = models.CharField(max_length=150, blank=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="cash")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Sale {self.product} · KSh {self.amount}"


# ---------- 10. Purchases ----------

class Purchase(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases")
    item = models.CharField(max_length=150)
    quantity = models.CharField(max_length=100, blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purchase_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-purchase_date"]

    def __str__(self):
        return f"{self.item} · KSh {self.cost}"


# ---------- 11. Weather Log ----------

class WeatherLog(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="weather", null=True, blank=True)
    date = models.DateField()
    rainfall_mm = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} · {self.rainfall_mm}mm"


# ---------- 12. Extension Visits ----------

class ExtensionVisit(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name="visits", null=True, blank=True)
    officer = models.CharField(max_length=150)
    date = models.DateField()
    recommendations = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.officer} · {self.date}"


# ---------- 13. Financial Records ----------

class FarmFinance(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name="finances", null=True, blank=True)
    date = models.DateField()
    income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loans = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subsidies = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    @property
    def profit(self):
        return float(self.income) - float(self.expenses)

    def __str__(self):
        return f"{self.date} · profit {self.profit}"


# ---------- Marketplace / POS (existing) ----------

class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64, unique=True, default=gen_uuid)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    category = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Listing(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="listings")
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product} ({self.owner})"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"), ("paid", "Paid"), ("shipped", "Shipped"),
        ("completed", "Completed"), ("cancelled", "Cancelled"),
    ]
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    items = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.total}"


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    event_type = models.CharField(max_length=50, default="training")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class AdvisoryRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="advisories")
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, default="open")
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.subject}"


class DeviceToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, default="web")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.platform}"