from rest_framework import serializers
from .models import (
    User, County, Commodity, MarketPrice, Event, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
    FarmerProfile, Farm, CropRecord, PlantingActivity, FarmInput,
    DiseaseReport, Harvest, InventoryItem, Sale, Purchase,
    WeatherLog, ExtensionVisit, FarmFinance,
)


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
    class Meta:
        model = Event
        fields = "__all__"


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

    class Meta:
        model = FarmerProfile
        fields = "__all__"
        read_only_fields = ["user", "farmer_id", "registration_date"]


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = "__all__"
        read_only_fields = ["farmer"]


class CropRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropRecord
        fields = "__all__"


class PlantingActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantingActivity
        fields = "__all__"


class FarmInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmInput
        fields = "__all__"


class DiseaseReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiseaseReport
        fields = "__all__"


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