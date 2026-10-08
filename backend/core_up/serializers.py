from rest_framework import serializers
from .models import (
    User, County, Commodity, MarketPrice, Event, EventRegistration, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
    FarmerProfile, Farm, CropRecord, PlantingActivity, FarmInput,
    DiseaseReport, DiseasePhoto, Harvest, InventoryItem, Sale, Purchase,
    WeatherLog, ExtensionVisit, FarmFinance, MAX_REPORT_PHOTOS,
)

# ------------------------------------------------------------------
# Image helpers — farmers upload from phones on slow connections, so cap the
# size and check the bytes really are an image before storing them.
# ------------------------------------------------------------------
MAX_IMAGE_BYTES = 6 * 1024 * 1024          # 6 MB per photo
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif"}


def absolute_media_url(request, file_or_path):
    """Return a URL the browser can load for an uploaded file.

    Accepts an ImageField, a FieldFile, or a plain string. Already-absolute URLs
    and data URIs (external ``photo_url`` values) pass through unchanged.
    """
    if not file_or_path:
        return ""
    value = str(file_or_path)
    if value.startswith(("http://", "https://", "data:")):
        return value
    # Only FieldFile objects expose .url; a plain path string does not.
    try:
        url = file_or_path.url
    except AttributeError:
        return value
    return request.build_absolute_uri(url) if request else url


def validate_uploaded_image(value):
    """Reject oversized or non-image uploads with a message a farmer can act on."""
    if value is None:
        return value
    size = getattr(value, "size", 0)
    if size and size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError(
            f"That photo is {size / 1048576:.1f} MB. Please use one under 6 MB."
        )
    content_type = (getattr(value, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise serializers.ValidationError(
            "Please upload a JPEG, PNG or WebP photo."
        )
    return value


# ---------- Auth ----------

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone", "first_name", "last_name",
            "is_staff", "is_phone_verified", "profile_completed", "password",
        ]
        read_only_fields = ["id", "is_staff", "is_phone_verified", "profile_completed"]


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if User.objects.filter(phone=attrs["phone"]).exists():
            raise serializers.ValidationError({"phone": "Phone already registered."})
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email already registered."})
        return attrs

    def create(self, validated_data):
        from .utils import generate_otp
        from django.utils import timezone
        otp = generate_otp()
        username = validated_data["email"].split("@")[0] + "_" + validated_data["phone"][-4:]
        user = User.objects.create_user(
            username=username,
            email=validated_data["email"],
            phone=validated_data["phone"],
            first_name=validated_data["name"],
            password=validated_data["password"],
            otp_code=otp,
        )
        user.otp_created_at = timezone.now()
        user.save()
        return user, otp


class OTPLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=6)


# ---------- Reference ----------

class CountySerializer(serializers.ModelSerializer):
    class Meta:
        model = County
        fields = "__all__"


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commodity
        fields = "__all__"


class MarketPriceSerializer(serializers.ModelSerializer):
    commodity_name = serializers.CharField(source="commodity.name", read_only=True)
    county_name = serializers.CharField(source="county.name", read_only=True)

    class Meta:
        model = MarketPrice
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    """Event payload for the Global & Local Events page.

    Exposes ready-to-use attendance details (``join_link``, ``join_code``,
    ``join_label``) so the frontend never has to guess how a farmer attends.
    """

    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    join_mode_display = serializers.CharField(source="get_join_mode_display", read_only=True)
    cost_display = serializers.CharField(source="get_cost_display", read_only=True)
    registrations_count = serializers.SerializerMethodField()
    is_full = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    join_link = serializers.CharField(source="resolved_join_url", read_only=True)
    join_code = serializers.CharField(source="resolved_join_code", read_only=True)
    tag_list = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "title", "description", "host", "location",
            "start_date", "end_date", "event_type", "event_type_display",
            "scope", "country", "region", "is_online",
            "join_mode", "join_mode_display", "join_link", "join_code",
            "access_link", "access_code", "whatsapp_link",
            "registration_required", "registration_url", "registration_deadline",
            "capacity", "registrations_count", "is_full", "is_past",
            "cost", "cost_display", "image_url", "source_url", "tags", "tag_list",
            "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_registrations_count(self, obj):
        return obj.registrations.exclude(status="cancelled").count()

    def get_tag_list(self, obj):
        return [t.strip() for t in (obj.tags or "").split(",") if t.strip()]


class EventRegistrationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)
    event_start = serializers.DateTimeField(source="event.start_date", read_only=True)
    join_mode = serializers.CharField(source="event.join_mode", read_only=True)
    join_link = serializers.CharField(source="event.resolved_join_url", read_only=True)
    join_code = serializers.CharField(source="event.resolved_join_code", read_only=True)

    class Meta:
        model = EventRegistration
        fields = [
            "id", "event", "event_title", "event_start", "full_name", "phone", "email",
            "county", "organisation", "status", "wants_reminder", "reference",
            "join_mode", "join_link", "join_code", "created_at",
        ]
        read_only_fields = ["id", "status", "reference", "created_at"]
        # DRF would auto-generate a UniqueTogetherValidator for the model's
        # (event, phone) constraint and reject duplicates with a generic field
        # error. Duplicate booking is handled in validate() instead, so the view
        # can return the farmer's existing place rather than a dead-end error.
        validators = []

    def validate_phone(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 9:
            raise serializers.ValidationError("Enter a valid phone number.")
        return value

    def validate(self, attrs):
        event = attrs.get("event")
        phone = attrs.get("phone")

        # Already booked? Flag the existing place on the serializer instead of
        # raising, so the view can return it (idempotent "Register" taps).
        # A ValidationError subclass would not survive DRF's re-wrapping here.
        existing = getattr(self, "_existing_registration", None)
        if existing is None and event and phone:
            existing = event.registrations.exclude(status="cancelled").filter(phone=phone).first()
            self._existing_registration = existing

        if existing is None:
            if event and event.is_past:
                raise serializers.ValidationError({"event": "This event has already ended."})
            if event and event.is_full:
                raise serializers.ValidationError({"event": "This event is fully booked."})
            if event and event.registration_deadline:
                from django.utils import timezone
                if timezone.localdate() > event.registration_deadline:
                    raise serializers.ValidationError({"event": "Registration for this event has closed."})
        return attrs

    @property
    def existing_registration(self):
        """The farmer's current booking for this event, if one already exists."""
        return getattr(self, "_existing_registration", None)


class AdvisoryRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvisoryRequest
        fields = "__all__"
        read_only_fields = ["user", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class ListingSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Listing
        fields = "__all__"
        read_only_fields = ["owner"]


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = "__all__"
        read_only_fields = ["user"]


# ---------- FMS ----------

class FarmerProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    national_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    county = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sub_county = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ward = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    village = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    farmer_group = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gps_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    gps_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    preferred_language = serializers.CharField(required=False, allow_blank=True, default="en")

    class Meta:
        model = FarmerProfile
        fields = "__all__"
        read_only_fields = ["user", "farmer_id", "registration_date"]

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            for key in ["national_id", "gender", "county", "sub_county", "ward", "village", "farmer_group"]:
                if key in data and data[key] is None:
                    data[key] = ""
            for key in ["date_of_birth", "gps_latitude", "gps_longitude"]:
                if key in data and data[key] == "":
                    data[key] = None
        return super().to_internal_value(data)


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = "__all__"
        read_only_fields = ["farmer"]


class CropRecordSerializer(serializers.ModelSerializer):
    """Crop record with an optional field photo.

    Accepts either an uploaded ``image`` (multipart, straight from a phone
    camera) or an external ``photo_url``. ``image_src`` is the single value the
    frontend should display.
    """

    image_src = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = CropRecord
        fields = "__all__"

    def get_image_src(self, obj):
        # Pass the file object, not the resolved string, so the URL can be made absolute.
        return absolute_media_url(self.context.get("request"), obj.image or obj.photo_url)

    def get_photo_count(self, obj):
        return 1 if obj.image_src else 0

    def validate_image(self, value):
        return validate_uploaded_image(value)


class PlantingActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantingActivity
        fields = "__all__"


class FarmInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmInput
        fields = "__all__"


class DiseasePhotoSerializer(serializers.ModelSerializer):
    image_src = serializers.SerializerMethodField()

    class Meta:
        model = DiseasePhoto
        fields = ["id", "report", "image", "image_src", "photo_stage", "caption", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_image_src(self, obj):
        return absolute_media_url(self.context.get("request"), obj.image)

    def validate_image(self, value):
        return validate_uploaded_image(value)


class DiseaseReportSerializer(serializers.ModelSerializer):
    """Disease report that accepts up to five photos of the affected crop.

    Farmers photograph the same plant from several angles (leaf close-up, whole
    plant, stem, roots), so the main ``image`` comes from the form and extra
    angles are posted under ``photos``.
    """

    image_src = serializers.SerializerMethodField()
    photos = DiseasePhotoSerializer(many=True, read_only=True)
    photo_count = serializers.SerializerMethodField()
    photo_stage_display = serializers.CharField(source="get_photo_stage_display", read_only=True)

    class Meta:
        model = DiseaseReport
        fields = "__all__"

    def get_image_src(self, obj):
        # Pass the file object, not the resolved string, so the URL can be made absolute.
        return absolute_media_url(self.context.get("request"), obj.image or obj.photo_url)

    def get_photo_count(self, obj):
        extra = getattr(obj, "photos", None)
        extra_count = extra.count() if extra is not None else 0
        return extra_count + (1 if (obj.image or obj.photo_url) else 0)

    def validate_image(self, value):
        return validate_uploaded_image(value)

    def create(self, validated_data):
        """Store the main photo plus any extra angles sent as ``images``.

        The farmer's phone posts every photo in one multipart request, so the
        extras are saved as DiseasePhoto rows for the same report.
        """
        report = super().create(validated_data)
        self.attach_extra_photos(report)
        return report

    def attach_extra_photos(self, report):
        request = self.context.get("request")
        if request is None:
            return []
        files = request.FILES.getlist("images") or request.FILES.getlist("extra_images")
        if not files:
            return []

        stages = request.data.getlist("photo_stage") if hasattr(request.data, "getlist") else []
        captions = request.data.getlist("caption") if hasattr(request.data, "getlist") else []

        created = []
        for index, upload in enumerate(files[:MAX_REPORT_PHOTOS]):
            try:
                validate_uploaded_image(upload)
            except serializers.ValidationError:
                continue
            created.append(DiseasePhoto.objects.create(
                report=report,
                image=upload,
                photo_stage=stages[index] if index < len(stages) else "",
                caption=captions[index] if index < len(captions) else "",
            ))
        return created

    def update(self, instance, validated_data):
        report = super().update(instance, validated_data)
        self.attach_extra_photos(report)
        return report

    def validate(self, attrs):
        # A report flagged for analysis must have something to analyse.
        needs = attrs.get("needs_analysis", getattr(self.instance, "needs_analysis", False))
        has_image = bool(
            attrs.get("image")
            or attrs.get("photo_url")
            or getattr(self.instance, "image", None)
            or getattr(self.instance, "photo_url", "")
        )
        if needs and not has_image and not self.partial:
            raise serializers.ValidationError(
                {"image": "Attach at least one photo so the disease can be assessed."}
            )
        return attrs


class HarvestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Harvest
        fields = "__all__"


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = "__all__"
        read_only_fields = ["farmer"]


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = "__all__"
        read_only_fields = ["farmer"]


class WeatherLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherLog
        fields = "__all__"


class ExtensionVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtensionVisit
        fields = "__all__"
        read_only_fields = ["farmer"]


class FarmFinanceSerializer(serializers.ModelSerializer):
    profit = serializers.ReadOnlyField()

    class Meta:
        model = FarmFinance
        fields = "__all__"
        read_only_fields = ["farmer"]