"""URL configuration for the FarmKonnect project.

Project-level routing only. All API routes live in ``backend.urls``
(see ``backend/urls.py``). This keeps the project URLconf small and
unaware of individual viewsets.
"""

from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("backend.urls")),
]