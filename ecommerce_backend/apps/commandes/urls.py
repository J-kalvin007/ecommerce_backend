from django.urls import path

from apps.commandes.views import (
    AdminOrderDetailAPIView,
    AdminOrderListAPIView,
    AdminOrderStatusAPIView,
    CheckoutAPIView,
    MyOrderListAPIView,
    OrderDetailAPIView,
    OrderHistoryAPIView,
)

app_name = "commandes"

urlpatterns = [
    # ==================================================
    # CLIENT
    # ==================================================
    path(
        "checkout/",
        CheckoutAPIView.as_view(),
        name="checkout",
    ),
    path(
        "",
        MyOrderListAPIView.as_view(),
        name="my-orders",
    ),
    path(
        "<str:reference>/",
        OrderDetailAPIView.as_view(),
        name="order-detail",
    ),
    path(
        "<str:reference>/history/",
        OrderHistoryAPIView.as_view(),
        name="order-history",
    ),

    # ==================================================
    # ADMIN
    # ==================================================
    path(
        "admin/",
        AdminOrderListAPIView.as_view(),
        name="admin-orders",
    ),
    path(
        "admin/<str:reference>/",
        AdminOrderDetailAPIView.as_view(),
        name="admin-order-detail",
    ),
    path(
        "admin/<str:reference>/status/",
        AdminOrderStatusAPIView.as_view(),
        name="admin-order-status",
    ),
]