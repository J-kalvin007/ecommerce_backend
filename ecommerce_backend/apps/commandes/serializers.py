


from rest_framework import serializers

from apps.commandes.models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    OrderStatus,
)


# =====================================================
# CHECKOUT
# =====================================================

class CheckoutItemSerializer(serializers.Serializer):

    product_id = serializers.UUIDField()

    quantity = serializers.IntegerField(
        min_value=1
    )


class CheckoutSerializer(serializers.Serializer):

    address_livraison = serializers.CharField(
        max_length=255
    )

    phone_livraison = serializers.CharField(
        max_length=30
    )

    city = serializers.CharField(
        max_length=100
    )

    country = serializers.CharField(
        max_length=100
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    items = CheckoutItemSerializer(
        many=True
    )

    def validate_items(self, value):

        if not value:
            raise serializers.ValidationError(
                "La commande doit contenir au moins un produit."
            )

        return value


# =====================================================
# ORDER ITEM
# =====================================================

class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:

        model = OrderItem

        fields = (
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "unit_price",
            "subtotal",
        )


# =====================================================
# ORDER LIST
# =====================================================

class OrderListSerializer(serializers.ModelSerializer):

    class Meta:

        model = Order

        fields = (
            "id",
            "reference",
            "status",
            "items_total",
            "frais_livraison",
            "total_final",
            "created_at",
        )


# =====================================================
# ORDER DETAIL
# =====================================================

class OrderDetailSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:

        model = Order

        fields = (
            "id",
            "reference",
            "status",

            "address_livraison",
            "phone_livraison",
            "city",
            "country",

            "items_total",
            "frais_livraison",
            "discount_amount",
            "tax_amount",
            "total_final",

            "notes",

            "paid_at",

            "created_at",
            "updated_at",

            "items",
        )


# =====================================================
# ORDER HISTORY
# =====================================================

class OrderHistorySerializer(
    serializers.ModelSerializer
):

    changed_by_email = serializers.SerializerMethodField()

    class Meta:

        model = OrderStatusHistory

        fields = (
            "id",
            "old_status",
            "new_status",
            "comment",
            "created_at",
            "changed_by_email",
        )

    def get_changed_by_email(
        self,
        obj,
    ):
        if not obj.changed_by:
            return None

        return obj.changed_by.email


# =====================================================
# ADMIN UPDATE STATUS
# =====================================================

class AdminOrderStatusSerializer(
    serializers.Serializer
):

    status = serializers.ChoiceField(
        choices=OrderStatus.choices
    )

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )