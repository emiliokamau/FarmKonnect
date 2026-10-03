"""API viewsets for Farmkonnect backend.

The views are deliberately thin – they delegate all heavy lifting to the
``services`` module and to ``django-filter`` for query parameters. Permissions
are role‑aware: farmers can create advisory requests and view their own, while
officers can list farmers and consult advisory outcomes. Admins have full
access.
"""

from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    User, MarketPrice, Event, AdvisoryRequest, County, 
    Commodity, Product, Listing, Order, DeviceToken
)
from .serializers import (
    UserSerializer,
    CountySerializer,
    CommoditySerializer,
    MarketPriceSerializer,
    EventSerializer,
    AdvisoryRequestSerializer,
    ProductSerializer,
    ListingSerializer,
    OrderSerializer,
    DeviceTokenSerializer,
)
from .services import generate_advisory, get_price_trend
from .csv_loader import load_prices_from_csv


# Marketplace viewsets
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["vendor", "price"]


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.filter(is_active=True)
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "unit_price", "is_active"]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["buyer", "status"]


class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["user", "platform"]


class RolePermission(BasePermission):
    """Custom permission class that checks the ``role`` attribute on ``User``.

    ``allowed_roles`` is defined on each view or action.
    """

    def has_permission(self, request, view):
        allowed = getattr(view, "allowed_roles", None)
        if allowed is None:
            return True
        return request.user.role in allowed

    def has_object_permission(self, request, view, obj):
        # Farmers can only access their own advisory requests
        if isinstance(obj, AdvisoryRequest) and request.user.role == "farmer":
            return obj.farmer_id == request.user.id
        return True


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role']


class CountyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = County.objects.all()
    serializer_class = CountySerializer
    permission_classes = [IsAuthenticated]


class CommodityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Commodity.objects.all()
    serializer_class = CommoditySerializer
    permission_classes = [IsAuthenticated]


class MarketPriceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketPrice.objects.select_related("commodity", "county").all()
    serializer_class = MarketPriceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "commodity__code": ["exact"],
        "county__name": ["exact"],
        "date": ["gte", "lte"]
    }

    @action(detail=False, methods=["get"], url_path="trend")
    def trend(self, request):
        """Return price trend for a commodity in a county.

        Expected query parameters:
            - ``commodity``: commodity code (e.g. MAIZE)
            - ``county``: county name
            - ``days``: number of past days (default 30)
        """
        commodity = request.query_params.get("commodity")
        county = request.query_params.get("county")
        days = int(request.query_params.get("days", 30))
        if not commodity or not county:
            return Response(
                {"detail": "commodity and county are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        data = get_price_trend(commodity, county, days=days)
        return Response(data)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.prefetch_related("counties").all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "category": ["exact"],
        "counties__name": ["exact"],
        "start_date": ["gte", "lte"]
    }


class AdvisoryRequestViewSet(viewsets.ModelViewSet):
    queryset = AdvisoryRequest.objects.select_related("farmer", "commodity").all()
    serializer_class = AdvisoryRequestSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    allowed_roles = ["farmer", "officer", "admin"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "farmer":
            return self.queryset.filter(farmer=user)
        return self.queryset

    def perform_create(self, serializer):
        serializer.save(farmer=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, RolePermission]
    )
    def run(self, request, pk=None):
        """Trigger AI advisory generation for the given request.
        """
        advisory = self.get_object()
        if advisory.recommendation:
            return Response(
                {"detail": "Advisory already processed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        generate_advisory(advisory.id)
        return Response(
            {"detail": "Advisory generated."},
            status=status.HTTP_200_OK
        )


class MarketPriceCsvViewSet(viewsets.ViewSet):
    """Read market price data from the latest CSV produced by the ETL.

    Supports ``commodity`` and ``county`` query params for filtering.
    Returns a list of price dicts compatible with ``MarketPriceSerializer``.
    """

    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"commodity": ["exact"], "county": ["exact"]}

    def list(self, request):
        commodity = request.query_params.get("commodity")
        county = request.query_params.get("county")
        data = load_prices_from_csv(commodity=commodity, county=county)
        if not data:
            return Response(
                {"detail": "No CSV data available"},
                status=status.HTTP_404_NOT_FOUND
            )
        # Use serializer for consistent field names
        serializer = MarketPriceSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)