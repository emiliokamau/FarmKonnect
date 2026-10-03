import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


def gen_uuid():
    return uuid.uuid4().hex[:12]


class User(AbstractUser):
    """Custom user with phone-based OTP login."""
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "phone"]

    def __str__(self):
        return self.username or self.phone or self.email


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


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    event_type = models.CharField(max_length=50, default="training")  # training|grant|subsidy
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class AdvisoryRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="advisories")
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, default="open")  # open|resolved
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.subject}"


# ---------- Marketplace / POS ----------

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
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
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


class DeviceToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, default="web")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.platform}"