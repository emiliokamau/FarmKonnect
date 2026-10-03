"""API URL configuration for the ``backend`` app.

Registers every viewset with a DRF router and exposes the resulting
router URLs under the app namespace. The project-level URLconf simply
does ``path("api/", include("backend.urls"))``.
"""

from rest_framework import routers

from .views import (
    # Marketplace
    ProductViewSet,
    ListingViewSet,
    OrderViewSet,
    DeviceTokenViewSet,
    # Reference data
    UserViewSet,
    CountyViewSet,
    CommodityViewSet,
    MarketPriceViewSet,
    EventViewSet,
    AdvisoryRequestViewSet,
    # CSV pass-through
    MarketPriceCsvViewSet,
)


# A single DefaultRouter instance for this app.
router = routers.DefaultRouter()

# Reference data
router.register(r"users", UserViewSet, basename="user")
router.register(r"counties", CountyViewSet, basename="county")
router.register(r"commodities", CommodityViewSet, basename="commodity")
router.register(r"prices", MarketPriceViewSet, basename="marketprice")
router.register(r"events", EventViewSet, basename="event")
router.register(r"advisories", AdvisoryRequestViewSet, basename="advisoryrequest")

# Marketplace
router.register(r"products", ProductViewSet, basename="product")
router.register(r"listings", ListingViewSet, basename="listing")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"device_tokens", DeviceTokenViewSet, basename="devicetoken")

# CSV pass-through (plain ViewSet; still registerable with a router)
router.register(r"prices_csv", MarketPriceCsvViewSet, basename="prices_csv")


urlpatterns = router.urls