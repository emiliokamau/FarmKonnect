import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def gen_uuid():
    return uuid.uuid4().hex[:12]


# A disease report holds one main photo plus this many extra angles.
MAX_REPORT_PHOTOS = 5


class User(AbstractUser):
    """Custom user with phone-based OTP login and role handling."""
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    profile_completed = models.BooleanField(default=False)
    ROLE_CHOICES = [
        ("FARMER", "Farmer"),
        ("OFFICER", "Extension Officer"),
        ("COMPANY", "Company / Buyer"),
        ("ADMIN", "Administrator"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="FARMER")

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

    # Field photos: an uploaded file from the farmer's phone, or a link.
    image = models.ImageField(
        upload_to="crops/%Y/%m/", null=True, blank=True,
        help_text="Photo of the crop or field",
    )
    photo_url = models.URLField(blank=True, help_text="Alternative: link to an image")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop} @ {self.farm.name}"

    @property
    def image_src(self):
        """Uploaded file wins; otherwise fall back to the external link."""
        if self.image:
            return self.image.url
        return self.photo_url or ""


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
    PHOTO_STAGE = [
        ("leaf", "Leaf / close-up"),
        ("whole_plant", "Whole plant"),
        ("stem", "Stem"),
        ("fruit", "Fruit / pod"),
        ("root", "Root"),
        ("field", "Whole field"),
    ]

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="diseases", null=True, blank=True)
    date = models.DateField()
    crop = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True)
    growth_stage = models.CharField(max_length=100, blank=True, help_text="e.g. seedling, flowering")
    symptoms = models.TextField(blank=True)
    affected_area = models.CharField(max_length=100, blank=True, help_text="e.g. about a quarter of the field")

    # --- photos the farmer uploads from the field ---
    image = models.ImageField(
        upload_to="diseases/%Y/%m/", null=True, blank=True,
        help_text="Main photo of the affected plant",
    )
    photo_stage = models.CharField(max_length=20, choices=PHOTO_STAGE, blank=True)
    photo_url = models.URLField(blank=True, help_text="Alternative: link to an image")

    diagnosis = models.CharField(max_length=200, blank=True)
    needs_analysis = models.BooleanField(
        default=False, help_text="Queued for disease analysis — no diagnosis recorded yet",
    )
    severity = models.CharField(max_length=10, choices=SEVERITY, default="low")
    treatment = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.crop} · {self.diagnosis or 'undiagnosed'}"

    @property
    def image_src(self):
        """Uploaded file wins; otherwise fall back to the external link."""
        if self.image:
            return self.image.url
        return self.photo_url or ""


class DiseasePhoto(models.Model):
    """Extra photos (up to four more angles) attached to one disease report."""

    report = models.ForeignKey(DiseaseReport, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="diseases/%Y/%m/")
    photo_stage = models.CharField(max_length=20, choices=DiseaseReport.PHOTO_STAGE, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.report.crop} photo #{self.pk}"


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
    """An agricultural event published to the Global & Local Events page.

    Events are either ``local`` (a specific place in the farmer's own county or
    country) or ``global`` (international / online). Hosts decide *how* farmers
    attend via ``join_mode``; ``join_url``/``access_link`` carry the Google Meet,
    Zoom or livestream destination, while ``whatsapp_link`` supports the
    WhatsApp groups that most farmer training programmes actually run on.
    """

    TYPE_CHOICES = [
        ("training", "Training / Workshop"),
        ("webinar", "Webinar"),
        ("conference", "Conference / Summit"),
        ("expo", "Exhibition / Expo"),
        ("field_day", "Field Day / Demo"),
        ("grant", "Grant / Funding Call"),
    ]
    SCOPE_CHOICES = [
        ("local", "Local"),
        ("global", "Global"),
    ]
    JOIN_MODE_CHOICES = [
        ("google_meet", "Google Meet"),
        ("zoom", "Zoom"),
        ("teams", "Microsoft Teams"),
        ("whatsapp", "WhatsApp Group"),
        ("livestream", "Livestream / YouTube"),
        ("website", "Register on host website"),
        ("in_person", "In person (venue)"),
        ("phone", "Phone / Dial-in"),
    ]
    COST_CHOICES = [
        ("free", "Free"),
        ("paid", "Paid"),
        ("sponsored", "Sponsored / Invitation only"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    host = models.CharField(max_length=200, blank=True, help_text="Organisation running the event")
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="training")
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default="local", db_index=True)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True, help_text="State / province / county")
    is_online = models.BooleanField(default=False)

    # --- how farmers attend ---
    join_mode = models.CharField(max_length=20, choices=JOIN_MODE_CHOICES, default="website")
    join_url = models.URLField(blank=True, help_text="Direct Google Meet / Zoom / livestream link")
    access_link = models.CharField(max_length=255, blank=True, help_text="Link or dial-in shown to farmers")
    access_code = models.CharField(max_length=100, blank=True, help_text="Passcode / dial-in PIN, shown after registering")
    whatsapp_link = models.URLField(blank=True)

    # --- registration ---
    registration_required = models.BooleanField(default=True)
    registration_url = models.URLField(blank=True)
    registration_deadline = models.DateField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)

    cost = models.CharField(max_length=20, choices=COST_CHOICES, default="free")
    image_url = models.URLField(blank=True)
    source_url = models.URLField(blank=True, help_text="Official event page, for verification")
    tags = models.CharField(max_length=255, blank=True, help_text="Comma separated keywords")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_date"]
        verbose_name = "Event"
        verbose_name_plural = "Events"
        indexes = [models.Index(fields=["scope", "start_date"])]

    def __str__(self):
        return self.title

    # -- derived helpers used by the API ---------------------------------
    @property
    def is_past(self):
        return self.end_date is not None and self.end_date < timezone.now()

    @property
    def is_full(self):
        if self.capacity is None:
            return False
        return self.registrations.count() >= self.capacity

    @property
    def resolved_join_url(self):
        """Best link a farmer can use to attend, whatever the host used."""
        if self.join_url:
            return self.join_url
        if self.access_link.startswith(("http://", "https://")):
            return self.access_link
        if self.join_mode == "whatsapp" and self.whatsapp_link:
            return self.whatsapp_link
        if self.registration_url:
            return self.registration_url
        return ""

    @property
    def resolved_join_code(self):
        """Shareable passcode / dial-in for the chosen mode."""
        if self.access_code:
            return self.access_code
        url = self.join_url or ""
        if "meet.google.com/" in url:
            return url.rstrip("/").split("/")[-1].split("?")[0]
        if self.join_mode == "phone" and self.access_link:
            return self.access_link
        return ""


class EventRegistration(models.Model):
    """A farmer's place at an event, with the access details they need to join."""

    STATUS_CHOICES = [
        ("registered", "Registered"),
        ("confirmed", "Confirmed"),
        ("attended", "Attended"),
        ("cancelled", "Cancelled"),
        ("waitlist", "Waitlisted"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(
        "core_up.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="event_registrations"
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    county = models.CharField(max_length=100, blank=True)
    organisation = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="registered")
    wants_reminder = models.BooleanField(default=True)
    # Booking reference the farmer can quote, and that unlocks the join link.
    reference = models.CharField(max_length=12, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"
        constraints = [
            models.UniqueConstraint(fields=["event", "phone"], name="unique_event_registration_phone"),
        ]

    def __str__(self):
        return f"{self.full_name} -> {self.event.title}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._make_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _make_reference():
        """Short, human-readable booking code, e.g. FK-7K2M4Q."""
        while True:
            code = f"FK-{uuid.uuid4().hex[:6].upper()}"
            if not EventRegistration.objects.filter(reference=code).exists():
                return code


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