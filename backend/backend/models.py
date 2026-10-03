"""Django models for the Farmkonnect agricultural portal.

This module defines the core relational schema, including:
- Custom user model with role-based permissions.
- Market price records for commodities per county.
- Events (training sessions or grant opportunities).
- Advisory requests used by the AI post‑harvest advisory service.

All models use standard Django conventions and include helpful string
representations and indexes for performant queries.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator
from typing import Literal


class User(AbstractUser):
    """Extended user model with role distinction.

    Roles:
        - ``farmer``: Regular farmer using the portal.
        - ``officer``: County‑level agricultural extension officer.
        - ``admin``: Platform administrators.
    """

    ROLE_CHOICES: list[tuple[Literal['farmer'], str], tuple[Literal['officer'], str], tuple[Literal['admin'], str]] = [
        ("farmer", "Farmer"),
        ("officer", "Extension Officer"),
        ("admin", "Administrator"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="farmer")

    def is_farmer(self) -> bool:
        return self.role == "farmer"

    def is_officer(self) -> bool:
        return self.role == "officer"

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"


class County(models.Model):
    """Kenyan county reference data.

    Stored as a separate model to enforce foreign‑key integrity and to allow
    easy expansion (e.g., adding region codes).
    """

    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "County"
        verbose_name_plural = "Counties"

    def __str__(self) -> str:
        return self.name


class Commodity(models.Model):
    """Supported agricultural commodities.

    The ``code`` field holds a short identifier such as ``MAIZE``.
    """

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Commodity"
        verbose_name_plural = "Commodities"

    def __str__(self) -> str:
        return self.name


class MarketPrice(models.Model):
    """Daily market price record for a commodity in a specific county.

    ``date`` is stored without time information because the source APIs
    provide daily aggregates.
    """

    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, related_name="prices")
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name="prices")
    date = models.DateField(default=timezone.now)
    wholesale_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    retail_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        unique_together = ("commodity", "county", "date")
        indexes = [
            models.Index(fields=["commodity", "county", "date"]),
        ]
        ordering = ["-date"]
        verbose_name = "Market Price"
        verbose_name_plural = "Market Prices"

    def __str__(self) -> str:
        return f"{self.commodity.code} - {self.county.name} @ {self.date}"


class Event(models.Model):
    """Training sessions, workshops, or grant opportunities.

    ``category`` distinguishes between educational events and financial grants.
    """

    CATEGORY_CHOICES: list[tuple[Literal['training'], str], tuple[Literal['grant'], str]] = [
        ("training", "Training / Workshop"),
        ("grant", "Grant Opportunity"),
    ]

    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=150)
    counties = models.ManyToManyField(County, related_name="events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self) -> str:
        return f"{self.title} ({self.get_category_display()})"


class AdvisoryRequest(models.Model):
    """User‑submitted request for AI post‑harvest advisory.

    ``recommendation`` is populated by the AI service after processing.
    ``price_snapshot`` stores a JSON‑serialised snapshot of the relevant
    market prices at the time of evaluation.
    """

    farmer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={"role": "farmer"})
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    harvest_date = models.DateField()
    storage_option = models.CharField(
        max_length=20,
        choices=[("immediate", "Sell Immediately"), ("store", "Store for Later")],
        default="immediate",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    recommendation = models.TextField(blank=True, null=True)
    price_snapshot = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Advisory Request"
        verbose_name_plural = "Advisory Requests"

    def __str__(self) -> str:
        return f"Advisory #{self.id} for {self.farmer.username}"

# Marketplace / E‑Commerce models

class Product(models.Model):
    """Agricultural product offered for sale by a farmer or officer."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return f"{self.name} (by {self.vendor.username})"

class Listing(models.Model):
    """A specific offering of a product with available quantity and optional custom price."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='listings')
    quantity_available = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Listing"
        verbose_name_plural = "Listings"

    def __str__(self):
        return f"Listing {self.id} for {self.product.name}"

class Order(models.Model):
    """Purchase of a listing by a buyer."""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name='orders')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.id} by {self.buyer.username}"

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.quantity * self.listing.unit_price
        super().save(*args, **kwargs)

# Push‑notification device token model
class DeviceToken(models.Model):
    """Stores FCM device registration tokens per user."""
    PLATFORM_CHOICES = [
        ("android", "Android"),
        ("ios", "iOS"),
        ("web", "Web"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Device Token"
        verbose_name_plural = "Device Tokens"

    def __str__(self):
        return f"{self.user.username} - {self.platform}"
