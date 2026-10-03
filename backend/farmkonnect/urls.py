"""URL configuration for FarmKonnect project.

Routes the API endpoints using a DRF router.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

from backend.views import (
    UserViewSet,
    CountyViewSet,
    CommodityViewSet,
    MarketPriceViewSet,
    EventViewSet,
    AdvisoryRequestViewSet,
    MarketPriceCsvViewSet,
)

router.register(r'prices_csv', MarketPriceCsvViewSet, basename='prices_csv')

router.register(r'products', ProductViewSet, basename='products')
router.register(r'listings', ListingViewSet, basename='listings')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'device_tokens', DeviceTokenViewSet, basename='device_tokens')
router.register(r'users', UserViewSet)
router.register(r'counties', CountyViewSet)
router.register(r'commodities', CommodityViewSet)
router.register(r'prices', MarketPriceViewSet)
router.register(r'events', EventViewSet)
router.register(r'advisories', AdvisoryRequestViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
