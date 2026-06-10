from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ToggleFavoriteView, MyFavoritesView, DeleteFavoriteView
from .views import RateProductView, ProductRatingDetailView, DeleteRatingView
from .views import (
    CategoryAdminViewSet,
    CategoryViewSet,
    ProductAdminViewSet,
    ProductImageAdminViewSet,
    ProductVariantAdminViewSet,
    ProductViewSet,
)

app_name = "catalog"

router = DefaultRouter()


# =====================================================
# PUBLIC API
# =====================================================

router.register(
    r"products",
    ProductViewSet,
    basename="products",
)

router.register(
    r"categories",
    CategoryViewSet,
    basename="categories",
)

# =====================================================
# ADMIN API
# =====================================================

router.register(
    r"admin/products",
    ProductAdminViewSet,
    basename="admin-products",
)

router.register(
    r"admin/categories",
    CategoryAdminViewSet,
    basename="admin-categories",
)

router.register(
    r"admin/product-images",
    ProductImageAdminViewSet,
    basename="admin-product-images",
)

router.register(
    r"admin/product-variants",
    ProductVariantAdminViewSet,
    basename="admin-product-variants",
)

urlpatterns = [
    path("", include(router.urls)),

    path(
        "toggle/",
        ToggleFavoriteView.as_view(),
        name="favorites-toggle",
    ),

    path(
        "my-favorites/",
        MyFavoritesView.as_view(),
        name="my-favorites",
    ),

    path(
        "<uuid:product_id>/",
        DeleteFavoriteView.as_view(),
        name="favorites-delete",
    ),


    path(
        "rate/",
        RateProductView.as_view(),
        name="ratings-rate",
    ),

    path(
        "<uuid:product_id>/",
        ProductRatingDetailView.as_view(),
        name="ratings-detail",
    ),

    path(
        "<uuid:product_id>/delete/",
        DeleteRatingView.as_view(),
        name="ratings-delete",
    ),



]





