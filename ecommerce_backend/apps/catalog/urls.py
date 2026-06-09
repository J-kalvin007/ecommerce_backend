


from rest_framework.routers import DefaultRouter

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

urlpatterns = router.urls