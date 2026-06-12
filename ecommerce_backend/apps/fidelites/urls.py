

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MyLoyaltyProfileView,
    TiersListView,
    RedeemPointsView,
    LoyaltyEventsView,
    AdminLoyaltyProfileViewSet,
)

admin_router = DefaultRouter()
admin_router.register(r"profiles", AdminLoyaltyProfileViewSet, basename="admin-loyalty-profiles")

urlpatterns = [

    path("mon-profil-fidelite/", MyLoyaltyProfileView.as_view(), name="mon-profil-fidelite"),

    path("liste-des-grades/", TiersListView.as_view(), name="liste-des-grades"),

    path("depenser-mes-points/", RedeemPointsView.as_view(), name="depenser-mes-points"),

    path("historique-utilisation/", LoyaltyEventsView.as_view(), name="historique-utilisation"),

    path("admin/", include(admin_router.urls)),

]