from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/api/agent/health/", permanent=False), name="home"),
    path("api/", include("agent.urls")),
]
