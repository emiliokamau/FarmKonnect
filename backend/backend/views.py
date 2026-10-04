from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.parsers import BaseParser

from .models import (
    User, County, Commodity, MarketPrice, Event, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
    FarmerProfile, Farm, CropRecord, PlantingActivity, FarmInput,
    DiseaseReport, Harvest, InventoryItem, Sale, Purchase,
    WeatherLog, ExtensionVisit, FarmFinance,
)
from .serializers import (
    UserSerializer, RegisterSerializer, OTPLoginSerializer,
    CountySerializer, CommoditySerializer, MarketPriceSerializer,
    EventSerializer, AdvisoryRequestSerializer,
    ProductSerializer, ListingSerializer, OrderSerializer, DeviceTokenSerializer,
    FarmerProfileSerializer, FarmSerializer, CropRecordSerializer,
    PlantingActivitySerializer, FarmInputSerializer, DiseaseReportSerializer,
    HarvestSerializer, InventoryItemSerializer, SaleSerializer,
    PurchaseSerializer, WeatherLogSerializer, ExtensionVisitSerializer,
    FarmFinanceSerializer,
)
from .permissions import IsAdminOrReadOnly
from .utils import generate_otp, otp_is_valid, send_otp


# ---------------- AUTH ----------------

@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user, otp = serializer.save()
    delivery = send_otp(user, otp, purpose="registration")
    return Response({
        "detail": "Registration successful. OTP sent.",
        "phone": user.phone,
        "email": user.email,
        "delivery": {
            "channel": delivery.get("channel"),
            "delivered": delivery.get("delivered"),
        },
        "otp_debug": otp,
    }, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def request_otp_view(request):
    phone = request.data.get("phone") or request.data.get("email")
    if not phone:
        return Response({"detail": "phone or email is required."}, status=400)
    user = (
        User.objects.filter(phone=phone).first()
        or User.objects.filter(email__iexact=phone).first()
    )
    if not user:
        return Response({"detail": "No account found."}, status=404)

    otp = generate_otp()
    user.otp_code = otp
    user.otp_created_at = timezone.now()
    user.save(update_fields=["otp_code", "otp_created_at"])

    delivery = send_otp(user, otp, purpose="login")
    return Response({
        "detail": "OTP sent.",
        "delivery": {"channel": delivery.get("channel"), "delivered": delivery.get("delivered")},
        "otp_debug": otp,
    })


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def verify_otp_view(request):
    serializer = OTPLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data["phone"]
    otp = serializer.validated_data["otp"]

    user = (
        User.objects.filter(phone=phone).first()
        or User.objects.filter(email__iexact=phone).first()
    )
    if not user:
        return Response({"detail": "Invalid identifier."}, status=404)
    if not otp_is_valid(user, otp):
        return Response({"detail": "Invalid or expired OTP."}, status=400)

    user.is_phone_verified = True
    user.otp_code = None
    user.save(update_fields=["is_phone_verified", "otp_code"])

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "user": UserSerializer(user).data,
        "profile_completed": user.profile_completed,
    })


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_password_view(request):
    ident = (request.data.get("phone") or request.data.get("email") or "").strip()
    password = request.data.get("password") or ""

    if not ident or not password:
        return Response({"detail": "Phone/email and password are required."}, status=400)

    user = (
        User.objects.filter(phone=ident).first()
        or User.objects.filter(email__iexact=ident).first()
        or User.objects.filter(username__iexact=ident).first()
    )
    if not user or not user.check_password(password):
        return Response({"detail": "Invalid credentials."}, status=400)

    otp = generate_otp()
    user.otp_code = otp
    user.otp_created_at = timezone.now()
    user.save(update_fields=["otp_code", "otp_created_at"])

    delivery = send_otp(user, otp, purpose="login")
    identifier = user.phone or user.email

    return Response({
        "detail": "Credentials verified. OTP sent.",
        "identifier": identifier,
        "delivery": {"channel": delivery.get("channel"), "delivered": delivery.get("delivered")},
        "otp_debug": otp,
    })


@csrf_exempt
@api_view(["POST"])
def logout_view(request):
    if request.user.is_authenticated:
        Token.objects.filter(user=request.user).delete()
    return Response({"detail": "Logged out."})


@api_view(["GET"])
def me_view(request):
    return Response(UserSerializer(request.user).data)


# ---------------- FARMER PROFILE ----------------

@csrf_exempt
@api_view(["GET", "PUT", "PATCH"])
def my_farmer_profile(request):
    """Get or update the current user's farmer profile."""
    profile, created = FarmerProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.first_name or request.user.username},
    )

    if request.method == "GET":
        return Response(FarmerProfileSerializer(profile).data)

    serializer = FarmerProfileSerializer(profile, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    # Mark profile complete
    if not request.user.profile_completed:
        request.user.profile_completed = True
        request.user.save(update_fields=["profile_completed"])

    return Response(serializer.data)


# ---------------- VIEWSETS ----------------

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnly]


class CountyViewSet(viewsets.ModelViewSet):
    queryset = County.objects.all().order_by("name")
    serializer_class = CountySerializer
    permission_classes = [IsAdminOrReadOnly]


class CommodityViewSet(viewsets.ModelViewSet):
    queryset = Commodity.objects.all().order_by("name")
    serializer_class = CommoditySerializer
    permission_classes = [IsAdminOrReadOnly]


class MarketPriceViewSet(viewsets.ModelViewSet):
    queryset = MarketPrice.objects.select_related("commodity", "county").all()
    serializer_class = MarketPriceSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["commodity", "county"]

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def trends(self, request):
        commodity = request.query_params.get("commodity")
        qs = self.get_queryset()
        if commodity:
            qs = qs.filter(commodity_id=commodity)
        return Response([
            {"date": p.date, "price": p.price, "commodity": p.commodity.name}
            for p in qs.order_by("date")[:200]
        ])


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by("-start_date")
    serializer_class = EventSerializer
    permission_classes = [IsAdminOrReadOnly]


class AdvisoryRequestViewSet(viewsets.ModelViewSet):
    queryset = AdvisoryRequest.objects.all().order_by("-created_at")
    serializer_class = AdvisoryRequestSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-id")
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.select_related("product", "owner").all()
    serializer_class = ListingSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        order = self.get_object()
        order.status = "paid"
        order.save(update_fields=["status"])
        return Response({"detail": "Order marked paid.", "id": order.id})


class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------- FMS: all viewsets filter by the current farmer ----------

class _FarmerScopedViewSet(viewsets.ModelViewSet):
    """Base class: every object belongs to the current user's farmer profile."""
    def _profile(self):
        return FarmerProfile.objects.filter(user=self.request.user).first()

    def get_queryset(self):
        p = self._profile()
        if not p:
            return self.queryset.none()
        return self.queryset.filter(farmer=p)

    def perform_create(self, serializer):
        p = self._profile()
        if not p:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Complete your farmer profile first.")
        serializer.save(farmer=p)


class _ProfileLookupMixin:
    """For models that reference FarmerProfile directly."""
    def _profile(self):
        return FarmerProfile.objects.filter(user=self.request.user).first()

    def get_queryset(self):
        p = self._profile()
        if not p:
            return self.queryset.none()
        return self.queryset.filter(farmer=p)

    def perform_create(self, serializer):
        p = self._profile()
        if not p:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Complete your farmer profile first.")
        serializer.save(farmer=p)


class FarmViewSet(_FarmerScopedViewSet):
    queryset = Farm.objects.all().order_by("-created_at")
    serializer_class = FarmSerializer


class CropRecordViewSet(viewsets.ModelViewSet):
    serializer_class = CropRecordSerializer

    def get_queryset(self):
        p = FarmerProfile.objects.filter(user=self.request.user).first()
        if not p:
            return CropRecord.objects.none()
        return CropRecord.objects.filter(farm__farmer=p).order_by("-created_at")


class PlantingActivityViewSet(viewsets.ModelViewSet):
    serializer_class = PlantingActivitySerializer

    def get_queryset(self):
        p = FarmerProfile.objects.filter(user=self.request.user).first()
        if not p:
            return PlantingActivity.objects.none()
        return PlantingActivity.objects.filter(farm__farmer=p).order_by("-date")


class FarmInputViewSet(viewsets.ModelViewSet):
    serializer_class = FarmInputSerializer

    def get_queryset(self):
        p = FarmerProfile.objects.filter(user=self.request.user).first()
        if not p:
            return FarmInput.objects.none()
        return FarmInput.objects.filter(farm__farmer=p).order_by("-application_date")


class DiseaseReportViewSet(viewsets.ModelViewSet):
    serializer_class = DiseaseReportSerializer

    def get_queryset(self):
        p = FarmerProfile.objects.filter(user=self.request.user).first()
        if not p:
            return DiseaseReport.objects.none()
        return DiseaseReport.objects.filter(farm__farmer=p).order_by("-date")


class HarvestViewSet(viewsets.ModelViewSet):
    serializer_class = HarvestSerializer

    def get_queryset(self):
        p = FarmerProfile.objects.filter(user=self.request.user).first()
        if not p:
            return Harvest.objects.none()
        return Harvest.objects.filter(farm__farmer=p).order_by("-harvest_date")


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        p = FarmerProfile.objects.filter(user=self.request.user).first()
        if not p:
            return InventoryItem.objects.none()
        return InventoryItem.objects.filter(farm__farmer=p)


class SaleViewSet(_ProfileLookupMixin, viewsets.ModelViewSet):
    queryset = Sale.objects.all().order_by("-date")
    serializer_class = SaleSerializer


class PurchaseViewSet(_ProfileLookupMixin, viewsets.ModelViewSet):
    queryset = Purchase.objects.all().order_by("-purchase_date")
    serializer_class = PurchaseSerializer


class WeatherLogViewSet(viewsets.ModelViewSet):
    serializer_class = WeatherLogSerializer

    def get_queryset(self):
        p = FarmerProfile.objects.filter(user=self.request.user).first()
        if not p:
            return WeatherLog.objects.none()
        return WeatherLog.objects.filter(farm__farmer=p).order_by("-date")


class ExtensionVisitViewSet(_ProfileLookupMixin, viewsets.ModelViewSet):
    queryset = ExtensionVisit.objects.all().order_by("-date")
    serializer_class = ExtensionVisitSerializer


class FarmFinanceViewSet(_ProfileLookupMixin, viewsets.ModelViewSet):
    queryset = FarmFinance.objects.all().order_by("-date")
    serializer_class = FarmFinanceSerializer


# ---------------- CSV PASS-THROUGH ----------------

class PlainTextParser(BaseParser):
    media_type = "text/csv"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read().decode("utf-8")


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def prices_csv(request):
    import csv
    from io import StringIO
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["commodity", "county", "price", "date", "source"])
    for p in MarketPrice.objects.select_related("commodity", "county").all():
        writer.writerow([p.commodity.name, p.county.name, p.price, p.date, p.source])
    return Response({"csv": buf.getvalue()})


class MarketPriceCsvViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        return prices_csv(request)