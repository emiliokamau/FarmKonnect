"""DRF serializers for Farmkonnect backend.

Each serializer mirrors a model and defines the fields that are exposed via the
API. Nested relationships are represented by primary‑key related fields to keep
payloads lightweight. Validation logic that depends on business rules is kept
minimal here – most complex checks live in ``services.py`` or viewsets.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    AdvisoryRequest,
    County,
    Commodity,
    MarketPrice,
    Event,
    Product,
    Listing,
    Order,
    DeviceToken,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role"]
        read_only_fields = ["id", "username"]


class CountySerializer(serializers.ModelSerializer):
    class Meta:
        model = County
        fields = ["id", "name"]
        read_only_fields = ["id"]


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commodity
        fields = ["id", "name", "code"]
        read_only_fields = ["id"]


class MarketPriceSerializer(serializers.ModelSerializer):
    commodity = serializers.SlugRelatedField(slug_field="code", queryset=Commodity.objects.all())
    county = serializers.SlugRelatedField(slug_field="name", queryset=County.objects.all())

    class Meta:
        model = MarketPrice
        fields = [
            "id",
            "commodity",
            "county",
            "date",
            "wholesale_price",
            "retail_price",
        ]
        read_only_fields = ["id"]


class EventSerializer(serializers.ModelSerializer):
    counties = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=County.objects.all()
    )

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "category",
            "start_date",
            "end_date",
            "location",
            "counties",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AdvisoryRequestSerializer(serializers.ModelSerializer):
    farmer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role="farmer"))
    commodity = serializers.SlugRelatedField(slug_field="code", queryset=Commodity.objects.all())

    class Meta:
        model = AdvisoryRequest
        fields = [
            "id",
            "farmer",
            "commodity",
            "quantity",
            "harvest_date",
            "storage_option",
            "created_at",
            "recommendation",
            "price_snapshot",
        ]
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "vendor", "created_at"]
        read_only_fields = ["id", "vendor", "created_at"]

class ListingSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    class Meta:
        model = Listing
        fields = ["id", "product", "quantity_available", "unit_price", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

class OrderSerializer(serializers.ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())
    class Meta:
        model = Order
        fields = ["id", "buyer", "listing", "quantity", "total_price", "status", "created_at"]
        read_only_fields = ["id", "total_price", "created_at"]

class DeviceTokenSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = DeviceToken
        fields = ["id", "user", "token", "platform", "created_at"]
        read_only_fields = ["id", "created_at"]

