from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from .models import ExtensionOfficer, Appointment
from .forms import OfficerRegistrationForm, AppointmentForm

class OfficerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "officer/dashboard.html"

    def test_func(self):
        return self.request.user.role == "OFFICER"

class AppointmentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Appointment
    template_name = "officer/appointment_list.html"
    context_object_name = "appointments"

    def get_queryset(self):
        # Officers see appointments assigned to them; farmers see theirs.
        user = self.request.user
        if user.role == "OFFICER":
            return Appointment.objects.filter(officer__user=user)
        else:
            return Appointment.objects.filter(farmer=user)

    def test_func(self):
        return self.request.user.role in ["OFFICER", "FARMER"]

class AppointmentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = "officer/appointment_form.html"
    success_url = reverse_lazy("officer:appointment_list")

    def form_valid(self, form):
        # Set the farmer to the logged‑in user (must be a farmer).
        form.instance.farmer = self.request.user
        return super().form_valid(form)

    def test_func(self):
        return self.request.user.role == "FARMER"

class AppointmentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Appointment
    template_name = "officer/appointment_detail.html"
    context_object_name = "appointment"

    def test_func(self):
        user = self.request.user
        # Officers can view appointments assigned to them; farmers can view their own.
        if user.role == "OFFICER":
            return self.get_object().officer.user == user
        elif user.role == "FARMER":
            return self.get_object().farmer == user
        return False
