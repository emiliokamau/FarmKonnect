from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.parsers import BaseParser

from .models import (
    User, County, Commodity, MarketPrice, Event, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
)
from .serializers import (
    UserSerializer, RegisterSerializer, OTPLoginSerializer,
    CountySerializer, CommoditySerializer, MarketPriceSerializer,
    EventSerializer, AdvisoryRequestSerializer,
    ProductSerializer, ListingSerializer, OrderSerializer, DeviceTokenSerializer,
)
from .permissions import IsAdminOrReadOnly
from .utils import generate_otp, otp_is_valid, send_sms


# ---------------- AUTH ----------------

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user, otp = serializer.save()
    send_sms(user.phone, f"Your FarmKonnect OTP is {otp}")
    return Response({
        "detail": "Registration successful. OTP sent to phone.",
        "phone": user.phone,
        "otp_debug": otp,  # remove in production
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def request_otp_view(request):
    """Send OTP to existing user's phone for login."""
    phone = request.data.get("phone")
    if not phone:
        return Response({"detail": "phone is required."}, status=400)
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({"detail": "No account with that phone."}, status=404)
    otp = generate_otp()
    user.otp_code = otp
    user.otp_created_at = timezone.now()
    user.save(update_fields=["otp_code", "otp_created_at"])
    send_sms(user.phone, f"Your FarmKonnect login OTP is {otp}")
    return Response({"detail": "OTP sent.", "otp_debug": otp})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def verify_otp_view(request):
    serializer = OTPLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data["phone"]
    otp = serializer.validated_data["otp"]
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({"detail": "Invalid phone."}, status=404)
    if not otp_is_valid(user, otp):
        return Response({"detail": "Invalid or expired OTP."}, status=400)
    user.is_phone_verified = True
    user.otp_code = None
    user.save(update_fields=["is_phone_verified", "otp_code"])
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "user": UserSerializer(user).data,
    })


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_password_view(request):
    """Optional: classic username/email + password login."""
    ident = request.data.get("username") or request.data.get("email") or request.data.get("phone")
    password = request.data.get("password")
    if not ident or not password:
        return Response({"detail": "credentials required."}, status=400)
    user = User.objects.filter(email=ident).first() or User.objects.filter(username=ident).first() or User.objects.filter(phone=ident).first()
    if not user or not user.check_password(password):
        return Response({"detail": "Invalid credentials."}, status=400)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["POST"])
def logout_view(request):
    if request.user.is_authenticated:
        Token.objects.filter(user=request.user).delete()
    return Response({"detail": "Logged out."})


@api_view(["GET"])
def me_view(request):
    return Response(UserSerializer(request.user).data)


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
        """Simple trend aggregation per commodity."""
        commodity = request.query_params.get("commodity")
        qs = self.get_queryset()
        if commodity:
            qs = qs.filter(commodity_id=commodity)
        data = [
            {"date": p.date, "price": p.price, "commodity": p.commodity.name}
            for p in qs.order_by("date")[:200]
        ]
        return Response(data)


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


# ---------------- CSV PASS-THROUGH ----------------

class PlainTextParser(BaseParser):
    media_type = "text/csv"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read().decode("utf-8")


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def prices_csv(request):
    """Return market prices as CSV text."""
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