from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Appointment

User = get_user_model()

class OfficerRegistrationForm(UserCreationForm):
    """Registration form for extension officers.
    Extends the base UserCreationForm with officer‑specific fields.
    """
    specialization = forms.CharField(max_length=100, required=False)
    region = forms.CharField(max_length=100, required=False)
    license_number = forms.CharField(max_length=50, required=True)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "phone", "password1", "password2",
                  "specialization", "region", "license_number")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "OFFICER"
        if commit:
            user.save()
            # Create the ExtensionOfficer profile
            from .models import ExtensionOfficer
            ExtensionOfficer.objects.create(
                user=user,
                specialization=self.cleaned_data.get("specialization", ""),
                region=self.cleaned_data.get("region", ""),
                license_number=self.cleaned_data["license_number"],
                phone=self.cleaned_data.get("phone", ""),
                verified=False,
            )
        return user


class AppointmentForm(forms.ModelForm):
    """Form for a farmer to book an appointment with an officer."""
    target_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    class Meta:
        model = Appointment
        fields = [
            "officer",
            "target_datetime",
            "location",
            "crop",
            "objectives",
        ]
        widgets = {
            "location": forms.TextInput(attrs={"placeholder": "Farm address or GPS"}),
            "crop": forms.TextInput(attrs={"placeholder": "Crop or livestock"}),
            "objectives": forms.Textarea(attrs={"rows": 3}),
        }
