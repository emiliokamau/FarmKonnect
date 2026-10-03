from django.urls import path, include
from rest_framework import routers

from .views import (
    ProductViewSet, ListingViewSet, OrderViewSet, DeviceTokenViewSet,
    UserViewSet, CountyViewSet, CommodityViewSet, MarketPriceViewSet,
    EventViewSet, AdvisoryRequestViewSet, MarketPriceCsvViewSet,
    register_view, request_otp_view, verify_otp_view,
    login_password_view, logout_view, me_view,
)

router = routers.DefaultRouter()

# Reference data
router.register(r"users", UserViewSet, basename="user")
router.register(r"counties", CountyViewSet, basename="county")
router.register(r"commodities", CommodityViewSet, basename="commodity")
router.register(r"prices", MarketPriceViewSet, basename="marketprice")
router.register(r"events", EventViewSet, basename="event")
router.register(r"advisories", AdvisoryRequestViewSet, basename="advisoryrequest")

# Marketplace / POS
router.register(r"products", ProductViewSet, basename="product")
router.register(r"listings", ListingViewSet, basename="listing")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"device_tokens", DeviceTokenViewSet, basename="devicetoken")

# CSV
router.register(r"prices_csv", MarketPriceCsvViewSet, basename="prices_csv")


auth_patterns = [
    path("auth/register/", register_view, name="auth-register"),
    path("auth/request-otp/", request_otp_view, name="auth-request-otp"),
    path("auth/verify-otp/", verify_otp_view, name="auth-verify-otp"),
    path("auth/login/", login_password_view, name="auth-login"),
    path("auth/logout/", logout_view, name="auth-logout"),
    path("auth/me/", me_view, name="auth-me"),
]

urlpatterns = auth_patterns + router.urls