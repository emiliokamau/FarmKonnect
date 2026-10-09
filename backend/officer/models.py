from django.conf import settings
from django.db import models

class ExtensionOfficer(models.Model):
    """Profile for extension officers, linked one-to-one with User."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='officer_profile')
    specialization = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.region})"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RESCHEDULED', 'Rescheduled'),
    ]
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    officer = models.ForeignKey(ExtensionOfficer, on_delete=models.CASCADE, related_name='appointments')
    target_datetime = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    crop = models.CharField(max_length=100, blank=True)
    objectives = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.farmer.username} ↔ {self.officer.user.username} @ {self.target_datetime:%Y-%m-%d %H:%M}"
