from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.views.static import serve as static_serve

from django.conf.urls.static import static

FRONTEND_DIR = settings.FRONTEND_DIR

urlpatterns = [
    # --- Admin & API ---
    path("admin/", admin.site.urls),
    path("api/konnect-ai/", include("konnect_ai.urls")),
    path("api/", include("backend.urls")),

    # --- Frontend HTML pages ---
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("index.html", TemplateView.as_view(template_name="index.html")),
    path("login.html", TemplateView.as_view(template_name="login.html")),
    path("register.html", TemplateView.as_view(template_name="register.html")),
    path("verify-otp.html", TemplateView.as_view(template_name="verify-otp.html")),
    path("dashboard.html", TemplateView.as_view(template_name="dashboard.html")),
    path("pos.html", TemplateView.as_view(template_name="pos.html")),
    path("farmer-portal.html", TemplateView.as_view(template_name="farmer-portal.html")),
    path("farmer-profile.html", TemplateView.as_view(template_name="farmer-profile.html")),

    # --- Frontend assets ---
    path("css/<path:path>", static_serve, {"document_root": FRONTEND_DIR / "css"}),
    path("js/<path:path>", static_serve, {"document_root": FRONTEND_DIR / "js"}),
    path("favicon.ico", static_serve, {"document_root": FRONTEND_DIR, "path": "favicon.ico"}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)