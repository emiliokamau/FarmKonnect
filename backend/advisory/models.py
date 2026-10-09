from django.db import models
from django.conf import settings

class AdvisoryPost(models.Model):
    CATEGORY_CHOICES = [
        ("PEST_DISEASE", "Pest/Disease"),
        ("WEATHER", "Weather Alert"),
        ("SOIL", "Soil"),
        ("GENERAL", "General"),
    ]
    SEVERITY_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("CRITICAL", "Critical"),
    ]
    title = models.CharField(max_length=200)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="advisories")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="INFO")
    content = models.TextField()
    image = models.ImageField(upload_to="advisories/", blank=True, null=True)
    target_crops = models.CharField(max_length=200, blank=True, help_text="Comma‑separated crop names")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
