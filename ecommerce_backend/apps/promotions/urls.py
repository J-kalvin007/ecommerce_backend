

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ActivePromoCodesView,
    ValidatePromoCodeView,
    ApplyPromoCodeView,
    ActiveFlashSalesView,
    ActiveBannersView,
    AdminPromoCodeViewSet,
    AdminFlashSaleViewSet,
    AdminBannerViewSet,
)

# Router admin
admin_router = DefaultRouter()
admin_router.register(r"codes", AdminPromoCodeViewSet, basename="admin-promo-codes")
admin_router.register(r"flash-sales", AdminFlashSaleViewSet, basename="admin-flash-sales")
admin_router.register(r"banners", AdminBannerViewSet, basename="admin-banners")

urlpatterns = [
    # Public
    path("codes/", ActivePromoCodesView.as_view(), name="active-promo-codes"),
    path("codes/validate/", ValidatePromoCodeView.as_view(), name="validate-promo-code"),
    path("codes/apply/", ApplyPromoCodeView.as_view(), name="apply-promo-code"),
    path("flash-sales/", ActiveFlashSalesView.as_view(), name="active-flash-sales"),
    path("banners/", ActiveBannersView.as_view(), name="active-banners"),
    # Admin
    path("admin/", include(admin_router.urls)),
]