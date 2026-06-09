from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.filters import (
    OrderingFilter,
    SearchFilter,
)

from rest_framework.permissions import (
    AllowAny,
)

from rest_framework.viewsets import (
    ModelViewSet,
    ReadOnlyModelViewSet,
)

from apps.core.permissions import (
    IsPlatformAdmin,
)

from .filters import ProductFilter

from .models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
)

from .serializers import (
    CategorySerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ProductVariantSerializer,
)


# =====================================================
# PUBLIC CATEGORY
# =====================================================

class CategoryViewSet(ReadOnlyModelViewSet):

    permission_classes = [AllowAny]

    serializer_class = CategorySerializer

    queryset = (
        Category.objects
        .filter(is_active=True)
        .prefetch_related("children")
    )


# =====================================================
# PUBLIC PRODUCT
# =====================================================

class ProductViewSet(ReadOnlyModelViewSet):

    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "description",
        "category__name",
        "sku",
    ]

    ordering_fields = [
        "price",
        "created_at",
        "name",
    ]

    queryset = (
        Product.objects
        .filter(is_active=True)
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
            "related_products",
        )
    )

    def get_serializer_class(self):

        if self.action == "retrieve":
            return ProductDetailSerializer

        return ProductListSerializer


# =====================================================
# ADMIN CATEGORY
# =====================================================

class CategoryAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    serializer_class = CategorySerializer

    queryset = (
        Category.objects
        .all()
        .prefetch_related("children")
    )


# =====================================================
# ADMIN PRODUCT
# =====================================================

class ProductAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    queryset = (
        Product.objects
        .all()
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
            "related_products",
        )
    )

    def get_serializer_class(self):

        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            return ProductCreateUpdateSerializer

        return ProductDetailSerializer


# =====================================================
# ADMIN PRODUCT IMAGE
# =====================================================

class ProductImageAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    serializer_class = ProductImageSerializer

    queryset = (
        ProductImage.objects
        .select_related("product")
    )


# =====================================================
# ADMIN PRODUCT VARIANT
# =====================================================

class ProductVariantAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    serializer_class = ProductVariantSerializer

    queryset = (
        ProductVariant.objects
        .select_related("product")
    )