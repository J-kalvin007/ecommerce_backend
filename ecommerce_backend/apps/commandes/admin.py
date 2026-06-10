
from django.contrib import admin

from apps.commandes.models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatusHistory,
)



class OrderItemInline(
    admin.TabularInline
):

    model = OrderItem

    extra = 0

    can_delete = False

    readonly_fields = (
        "product",
        "product_name",
        "product_sku",
        "quantity",
        "unit_price",
        "subtotal",
    )



class OrderStatusHistoryInline(
    admin.TabularInline
):

    model = OrderStatusHistory

    extra = 0

    can_delete = False

    readonly_fields = (
        "old_status",
        "new_status",
        "comment",
        "changed_by",
        "created_at",
    )




@admin.register(Cart)
class CartAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "user",
        "created_at",
        "updated_at",
        "is_active",
    )

    search_fields = (
        "user__email",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_active",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")



@admin.register(CartItem)
class CartItemAdmin(
    admin.ModelAdmin
):

    list_display = (
        "cart",
        "product",
        "quantity",
        "created_at",
    )

    search_fields = (
        "product__name",
        "product__sku",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("cart__user", "product")



@admin.register(Order)
class OrderAdmin(
    admin.ModelAdmin
):

    list_display = (
        "reference",
        "user",
        "status",
        "city",
        "country",
        "items_total",
        "total_final",
        "paid_at",
        "created_at",
    )

    list_filter = (
        "status",
        "country",
        "city",
        "created_at",
    )

    search_fields = (
        "reference",
        "user__email",
        "phone_livraison",
    )

    ordering = (
        "-created_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    readonly_fields = (
        "id",
        "reference",
        "created_at",
        "updated_at",
        "items_total",
        "discount_amount",
        "tax_amount",
        "frais_livraison",
        "total_final",
    )

    inlines = [
        OrderItemInline,
        OrderStatusHistoryInline,
    ]

    fieldsets = (

        (
            "Informations générales",
            {
                "fields": (
                    "id",
                    "reference",
                    "user",
                    "status",
                )
            },
        ),

        (
            "Livraison",
            {
                "fields": (
                    "address_livraison",
                    "phone_livraison",
                    "city",
                    "country",
                )
            },
        ),

        (
            "Montants",
            {
                "fields": (
                    "items_total",
                    "discount_amount",
                    "tax_amount",
                    "frais_livraison",
                    "total_final",
                )
            },
        ),

        (
            "Paiement",
            {
                "fields": (
                    "paid_at",
                )
            },
        ),

        (
            "Informations complémentaires",
            {
                "fields": (
                    "notes",
                )
            },
        ),

        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )






@admin.register(OrderItem)
class OrderItemAdmin(
    admin.ModelAdmin
):

    list_display = (
        "order",
        "product_name",
        "product_sku",
        "quantity",
        "unit_price",
        "subtotal",
    )

    search_fields = (
        "product_name",
        "product_sku",
        "order__reference",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order")




@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(
    admin.ModelAdmin
):

    list_display = (
        "order",
        "old_status",
        "new_status",
        "changed_by",
        "created_at",
    )

    search_fields = (
        "order__reference",
    )

    list_filter = (
        "new_status",
        "created_at",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order", "changed_by")