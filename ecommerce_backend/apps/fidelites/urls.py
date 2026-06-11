

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MyLoyaltyProfileView,
    TiersListView,
    RedeemPointsView,
    LoyaltyEventsView,
    ReferralView,
    AdminLoyaltyProfileViewSet,
)

admin_router = DefaultRouter()
admin_router.register(r"profiles", AdminLoyaltyProfileViewSet, basename="admin-loyalty-profiles")

urlpatterns = [
    path("me/", MyLoyaltyProfileView.as_view(), name="my-loyalty-profile"),
    path("tiers/", TiersListView.as_view(), name="loyalty-tiers"),
    path("points/redeem/", RedeemPointsView.as_view(), name="redeem-points"),
    path("events/", LoyaltyEventsView.as_view(), name="loyalty-events"),
    path("referral/", ReferralView.as_view(), name="loyalty-referral"),
    path("admin/", include(admin_router.urls)),
]