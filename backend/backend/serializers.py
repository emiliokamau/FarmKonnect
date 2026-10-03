from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import (
    User, County, Commodity, MarketPrice, Event, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone", "first_name", "last_name",
            "is_staff", "is_phone_verified", "password",
        ]
        read_only_fields = ["id", "is_staff", "is_phone_verified"]

    def create(self, validated_data):
        pwd = validated_data.pop("password", None)
        user = User(**validated_data)
        if pwd:
            user.set_password(pwd)
        else:
            user.set_unusable_password()
        user.save()
        return user


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
        user.otp_created_at = __import__("django.utils.timezone", fromlist=["now"]).now()
        user.save()
        return user, otp


class OTPLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=6)


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