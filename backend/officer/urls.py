from django.urls import path
from . import views

app_name = "officer"

urlpatterns = [
    path("", views.OfficerDashboardView.as_view(), name="dashboard"),
    path("appointments/", views.AppointmentListView.as_view(), name="appointment_list"),
    path("appointments/new/", views.AppointmentCreateView.as_view(), name="appointment_create"),
    path("appointments/<int:pk>/", views.AppointmentDetailView.as_view(), name="appointment_detail"),
]
