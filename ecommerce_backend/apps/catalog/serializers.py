from rest_framework import serializers

from .models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
)


# =====================================================
# CATEGORY
# =====================================================

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "image",
            "children",
        )

    def get_children(self, obj):
        return CategorySerializer(
            obj.children.all(),
            many=True
        ).data


# =====================================================
# PRODUCT IMAGE
# =====================================================

class ProductImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage
        fields = (
            "id",
            "image",
            "alt_text",
            "is_primary",
        )


# =====================================================
# PRODUCT VARIANT
# =====================================================

class ProductVariantSerializer(serializers.ModelSerializer):

    is_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant

        fields = (
            "id",
            "name",
            "sku",
            "price",
            "stock",
            "weight_grams",
            "is_in_stock",
        )

    def get_is_in_stock(self, obj):
        return obj.stock > 0


# =====================================================
# PRODUCT LIST
# =====================================================

class ProductListSerializer(serializers.ModelSerializer):

    primary_image = serializers.SerializerMethodField()

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = Product

        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "price",
            "stock",
            "is_top",
            "product_type",
            "category_name",
            "primary_image",
        )

    def get_primary_image(self, obj):
        image = obj.images.filter(
            is_primary=True
        ).first()

        if image:
            return ProductImageSerializer(image).data

        return None


# =====================================================
# PRODUCT DETAIL
# =====================================================

class ProductDetailSerializer(ProductListSerializer):

    images = ProductImageSerializer(
        many=True,
        read_only=True,
    )

    variants = ProductVariantSerializer(
        many=True,
        read_only=True,
    )

    related_products = ProductListSerializer(
        many=True,
        read_only=True,
    )

    category = CategorySerializer(
        read_only=True,
    )

    is_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "description",
            "product_type",
            "price",
            "stock",
            "weight_grams",
            "seo_title",
            "seo_description",
            "is_top",
            "is_in_stock",
            "category",
            "images",
            "variants",
            "related_products",
            "created_at",
            "updated_at",
        )

    def get_is_in_stock(self, obj):
        return obj.stock > 0


# =====================================================
# PRODUCT CREATE / UPDATE
# =====================================================

class ProductCreateUpdateSerializer(
    serializers.ModelSerializer
):

    images = ProductImageSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = Product

        fields = (
            "category",
            "name",
            "slug",
            "sku",
            "description",
            "product_type",
            "price",
            "stock",
            "weight_grams",
            "seo_title",
            "seo_description",
            "is_top",
            "related_products",
            "images",
        )

    def validate_sku(self, value):

        qs = Product.objects.filter(
            sku=value
        )

        if self.instance:
            qs = qs.exclude(
                pk=self.instance.pk
            )

        if qs.exists():
            raise serializers.ValidationError(
                "SKU already exists."
            )

        return value

    def create(self, validated_data):

        images_data = validated_data.pop(
            "images",
            []
        )

        product = Product.objects.create(
            **validated_data
        )

        for image_data in images_data:

            ProductImage.objects.create(
                product=product,
                **image_data
            )

        return product

    def update(
        self,
        instance,
        validated_data
    ):

        images_data = validated_data.pop(
            "images",
            None
        )

        for attr, value in validated_data.items():
            setattr(
                instance,
                attr,
                value
            )

        instance.save()

        if images_data:

            for image_data in images_data:

                ProductImage.objects.create(
                    product=instance,
                    **image_data
                )

        return instance