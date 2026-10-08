from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.parsers import BaseParser, MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    User, County, Commodity, MarketPrice, Event, EventRegistration, AdvisoryRequest,
    Product, Listing, Order, DeviceToken,
    FarmerProfile, Farm, CropRecord, PlantingActivity, FarmInput,
    DiseaseReport, DiseasePhoto, Harvest, InventoryItem, Sale, Purchase,
    WeatherLog, ExtensionVisit, FarmFinance, MAX_REPORT_PHOTOS,
)
from .serializers import (
    UserSerializer, RegisterSerializer, OTPLoginSerializer,
    CountySerializer, CommoditySerializer, MarketPriceSerializer,
    EventSerializer, EventRegistrationSerializer, AdvisoryRequestSerializer,
    ProductSerializer, ListingSerializer, OrderSerializer, DeviceTokenSerializer,
    FarmerProfileSerializer, FarmSerializer, CropRecordSerializer,
    PlantingActivitySerializer, FarmInputSerializer, DiseaseReportSerializer,
    DiseasePhotoSerializer, validate_uploaded_image,
    HarvestSerializer, InventoryItemSerializer, SaleSerializer,
    PurchaseSerializer, WeatherLogSerializer, ExtensionVisitSerializer,
    FarmFinanceSerializer,
)
from .permissions import IsAdminOrReadOnly
from .utils import generate_otp, otp_is_valid, send_otp

from django.db import IntegrityError
from django.db.models import Q


def farmer_profile_for(request):
    """The logged-in user's farmer profile, or None.

    Returns None for anonymous requests: filtering ``FarmerProfile`` by an
    AnonymousUser raises TypeError rather than a clean 401, which surfaced as a
    500 on every farmer-scoped endpoint.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    return FarmerProfile.objects.filter(user=user).first()


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
    """Global & Local agricultural events.

    Public (read-only) listing with search + filters so the events page can show
    both worldwide and nearby opportunities. Staff publish events, which are
    then immediately joinable by farmers.
    """

    serializer_class = EventSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Event.objects.prefetch_related("registrations").all()

        scope = self.request.query_params.get("scope")
        if scope in {"local", "global"}:
            qs = qs.filter(scope=scope)

        event_type = self.request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        join_mode = self.request.query_params.get("join_mode")
        if join_mode:
            qs = qs.filter(join_mode=join_mode)

        country = self.request.query_params.get("country")
        if country:
            qs = qs.filter(country__icontains=country)

        region = self.request.query_params.get("region")
        if region:
            qs = qs.filter(region__icontains=region)

        if self.request.query_params.get("online") in {"1", "true", "True"}:
            qs = qs.filter(is_online=True)

        if self.request.query_params.get("free") in {"1", "true", "True"}:
            qs = qs.filter(cost="free")

        # "upcoming" (default view) / "past" / "all"
        window = self.request.query_params.get("window", "upcoming")
        now = timezone.now()
        if window == "upcoming":
            qs = qs.filter(Q(end_date__gte=now) | Q(end_date__isnull=True, start_date__gte=now))
            qs = qs.filter(is_active=True)
        elif window == "past":
            qs = qs.filter(Q(end_date__lt=now) | Q(end_date__isnull=True, start_date__lt=now))

        # free-text search across the fields a farmer would think of
        search = self.request.query_params.get("search") or self.request.query_params.get("q")
        if search:
            for term in search.split():
                qs = qs.filter(
                    Q(title__icontains=term)
                    | Q(description__icontains=term)
                    | Q(host__icontains=term)
                    | Q(location__icontains=term)
                    | Q(region__icontains=term)
                    | Q(country__icontains=term)
                    | Q(tags__icontains=term)
                    | Q(event_type__icontains=term)
                )

        return qs.order_by("start_date")

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def summary(self, request):
        """Counts for the page header: how many local vs global are open."""
        now = timezone.now()
        upcoming = Event.objects.filter(is_active=True).filter(
            Q(end_date__gte=now) | Q(end_date__isnull=True, start_date__gte=now)
        )
        return Response({
            "total": upcoming.count(),
            "global": upcoming.filter(scope="global").count(),
            "local": upcoming.filter(scope="local").count(),
            "online": upcoming.filter(is_online=True).count(),
            "free": upcoming.filter(cost="free").count(),
        })

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.AllowAny])
    def join(self, request, pk=None):
        """Return (GET) or issue (POST) the attendance details for an event.

        This is what the **Join** button calls: it hands the farmer the exact
        Google Meet / Zoom / WhatsApp destination the host configured, without
        exposing passcodes to people who have not registered.
        """
        event = self.get_object()

        if request.method == "GET":
            return Response({
                "event": event.id,
                "title": event.title,
                "join_mode": event.join_mode,
                "join_mode_display": event.get_join_mode_display(),
                "join_link": event.resolved_join_url,
                "join_code": event.resolved_join_code,
                "location": event.location,
                "start_date": event.start_date,
                "registration_required": event.registration_required,
                "is_past": event.is_past,
            })

        # POST = a farmer tapping "Join". Confirm their place and release details.
        registration = None
        if request.user.is_authenticated:
            registration = event.registrations.filter(user=request.user).first()
        reference = request.data.get("reference")
        if registration is None and reference:
            registration = event.registrations.filter(reference=reference).first()

        if registration is None:
            if event.registration_required:
                return Response(
                    {"detail": "Please register for this event first.", "needs_registration": True},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({
                "join_link": event.resolved_join_url,
                "join_code": event.resolved_join_code,
                "join_mode_display": event.get_join_mode_display(),
            })

        return Response({
            "reference": registration.reference,
            "status": registration.status,
            "join_link": event.resolved_join_url,
            "join_code": event.resolved_join_code,
            "join_mode_display": event.get_join_mode_display(),
            "start_date": event.start_date,
        })


class EventRegistrationViewSet(viewsets.ModelViewSet):
    """Farmers register for an event and receive a booking reference."""

    serializer_class = EventRegistrationSerializer
    queryset = EventRegistration.objects.select_related("event").all()

    def get_permissions(self):
        # Farmers usually register and cancel without an account; a cancellation
        # is authorised by the booking reference instead of a login.
        if self.action in {"create", "cancel"}:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = self.queryset
        # Cancellation is authorised by the booking reference inside the action,
        # so the row must be reachable even for a farmer with no account.
        if self.action == "cancel":
            return qs
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(Q(user=user) | Q(phone=user.phone or ""))
        return qs.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Already registered with this phone — hand the place back rather than
        # dead-ending the farmer with a duplicate error.
        existing = serializer.existing_registration
        if existing:
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        event = serializer.validated_data["event"]
        phone = serializer.validated_data["phone"]

        try:
            registration = serializer.save(
                user=request.user if request.user.is_authenticated else None
            )
        except IntegrityError:
            existing = event.registrations.filter(phone=phone).first()
            if existing is None:
                raise
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        return Response(self.get_serializer(registration).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def cancel(self, request, pk=None):
        """Cancel a place. Requires the booking reference issued to the farmer.

        Anonymous is allowed here because most farmers register without an
        account; the reference is the secret that authorises the cancellation.
        """
        registration = self.get_object()
        reference = (request.data.get("reference") or "").strip()
        if not reference or reference.upper() != registration.reference.upper():
            return Response(
                {"detail": "Booking reference does not match."},
                status=status.HTTP_403_FORBIDDEN,
            )
        registration.status = "cancelled"
        registration.save(update_fields=["status"])
        return Response({"detail": "Registration cancelled.", "status": registration.status})


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
        return farmer_profile_for(self.request)

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
        return farmer_profile_for(self.request)

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
    # JSON plus multipart so a crop photo can be uploaded straight from a phone.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_context(self):
        # Multipart uploads do not add the request automatically, but the
        # serializer needs it to build absolute photo URLs.
        context = super().get_serializer_context()
        context.setdefault("request", self.request)
        return context

    def get_queryset(self):
        p = farmer_profile_for(self.request)
        if not p:
            return CropRecord.objects.none()
        return CropRecord.objects.filter(farm__farmer=p).order_by("-created_at")


class PlantingActivityViewSet(viewsets.ModelViewSet):
    serializer_class = PlantingActivitySerializer

    def get_queryset(self):
        p = farmer_profile_for(self.request)
        if not p:
            return PlantingActivity.objects.none()
        return PlantingActivity.objects.filter(farm__farmer=p).order_by("-date")


class FarmInputViewSet(viewsets.ModelViewSet):
    serializer_class = FarmInputSerializer

    def get_queryset(self):
        p = farmer_profile_for(self.request)
        if not p:
            return FarmInput.objects.none()
        return FarmInput.objects.filter(farm__farmer=p).order_by("-application_date")


class DiseaseReportViewSet(viewsets.ModelViewSet):
    serializer_class = DiseaseReportSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_context(self):
        # Multipart uploads do not add the request automatically, but the
        # serializer needs it to build absolute photo URLs.
        context = super().get_serializer_context()
        context.setdefault("request", self.request)
        return context

    def get_queryset(self):
        p = farmer_profile_for(self.request)
        if not p:
            return DiseaseReport.objects.none()
        return DiseaseReport.objects.filter(farm__farmer=p).order_by("-date")

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def add_photos(self, request, pk=None):
        """Attach extra angles to a report the farmer already sent.

        The farmer photographs the same plant from several sides; each file is
        stored as a DiseasePhoto (maximum five per report).
        """
        report = self.get_object()
        files = request.FILES.getlist("images") or request.FILES.getlist("image")
        if not files:
            return Response(
                {"detail": "No photos received. Attach one or more image files."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stages = request.data.getlist("photo_stage") if hasattr(request.data, "getlist") else []
        remaining = MAX_REPORT_PHOTOS - report.photos.count()
        if remaining <= 0:
            return Response(
                {"detail": f"This report already has the maximum of {MAX_REPORT_PHOTOS} extra photos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created, errors = [], []
        for index, upload in enumerate(files[:remaining]):
            try:
                validate_uploaded_image(upload)
            except serializers.ValidationError as exc:
                errors.append({"file": upload.name, "detail": exc.detail})
                continue
            photo = DiseasePhoto.objects.create(
                report=report,
                image=upload,
                photo_stage=stages[index] if index < len(stages) else "",
            )
            created.append(DiseasePhotoSerializer(photo, context={"request": request}).data)

        payload = {
            "added": len(created),
            "photos": created,
            "photo_count": report.photos.count(),
            "skipped": len(files) - len(created),
        }
        if errors:
            payload["errors"] = errors
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"], url_path="photos/(?P<photo_id>[^/.]+)")
    def remove_photo(self, request, pk=None, photo_id=None):
        """Remove one of the extra photos from a report."""
        report = self.get_object()
        photo = report.photos.filter(pk=photo_id).first()
        if photo is None:
            return Response({"detail": "Photo not found on this report."}, status=status.HTTP_404_NOT_FOUND)
        photo.image.delete(save=False)
        photo.delete()
        return Response({"detail": "Photo removed.", "photo_count": report.photos.count()})

    @action(detail=True, methods=["post"])
    def analyse(self, request, pk=None):
        """Queue a report for disease analysis.

        The image is already stored, so this just marks the report as awaiting a
        diagnosis and returns what the analyst or diagnosis service needs.
        """
        report = self.get_object()
        if not report.image_src:
            return Response(
                {"detail": "Attach at least one photo before requesting analysis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if report.diagnosis and not report.needs_analysis:
            return Response(
                {"detail": "This report already has a diagnosis.", "diagnosis": report.diagnosis},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report.needs_analysis = True
        report.save(update_fields=["needs_analysis"])
        return Response({
            "detail": "Report queued for analysis.",
            "report": self.get_serializer(report).data,
        })

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Reports still waiting for a diagnosis (for officers and analysts)."""
        qs = self.get_queryset().filter(needs_analysis=True)
        return Response(self.get_serializer(qs, many=True).data)


class DiseasePhotoViewSet(viewsets.ModelViewSet):
    """Standalone photo endpoint.

    Lets a farmer attach a picture to a report created earlier, including from
    the dashboard where the photo may be chosen after the record is saved.
    """

    serializer_class = DiseasePhotoSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        p = farmer_profile_for(self.request)
        if not p:
            return DiseasePhoto.objects.none()
        return DiseasePhoto.objects.filter(report__farm__farmer=p).order_by("id")

    def perform_create(self, serializer):
        report = serializer.validated_data["report"]
        p = farmer_profile_for(self.request)
        if report.farm and p and report.farm.farmer_id != p.id:
            raise PermissionDenied("That report belongs to another farm.")
        if report.photos.count() >= MAX_REPORT_PHOTOS:
            raise ValidationError(
                {"detail": f"A report can hold at most {MAX_REPORT_PHOTOS} extra photos."}
            )
        serializer.save()


class HarvestViewSet(viewsets.ModelViewSet):
    serializer_class = HarvestSerializer

    def get_queryset(self):
        p = farmer_profile_for(self.request)
        if not p:
            return Harvest.objects.none()
        return Harvest.objects.filter(farm__farmer=p).order_by("-harvest_date")


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        p = farmer_profile_for(self.request)
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
        p = farmer_profile_for(self.request)
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