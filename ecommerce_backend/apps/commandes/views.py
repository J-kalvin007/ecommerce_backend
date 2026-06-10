from django.shortcuts import render

from django.shortcuts import get_object_or_404

from django_filters.rest_framework import (
    DjangoFilterBackend,
)

from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response

from apps.core.permissions import (
    IsCustomer,
    IsPlatformAdmin,
)

from apps.commandes.filters import (
    OrderFilter,
)

from apps.commandes.models import (
    Order,
)

from apps.commandes.serializers import (
    CheckoutSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderHistorySerializer,
    AdminOrderStatusSerializer,
)

from apps.commandes.services import (
    OrderService,
)







class CheckoutAPIView(
    generics.GenericAPIView
):

    permission_classes = [
        IsAuthenticated,
        IsCustomer,
    ]

    serializer_class = CheckoutSerializer

    def post(self, request):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        order = OrderService.create_order(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )
    





class MyOrderListAPIView(
    generics.ListAPIView
):

    serializer_class = (
        OrderListSerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsCustomer,
    ]

    filterset_class = (
        OrderFilter
    )

    filter_backends = [
        DjangoFilterBackend,
    ]

    ordering = [
        "-created_at"
    ]

    def get_queryset(self):

        return (
            Order.objects
            .filter(
                user=self.request.user
            )
            .order_by(
                "-created_at"
            )
        )
    





class OrderDetailAPIView(
    generics.RetrieveAPIView
):

    serializer_class = (
        OrderDetailSerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsCustomer,
    ]

    lookup_field = (
        "reference"
    )

    def get_queryset(self):

        return (
            Order.objects
            .filter(
                user=self.request.user
            )
            .prefetch_related(
                "items"
            )
        )
    





class OrderHistoryAPIView(
    generics.ListAPIView
):

    serializer_class = (
        OrderHistorySerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsCustomer,
    ]

    def get_queryset(self):

        reference = self.kwargs[
            "reference"
        ]

        order = get_object_or_404(
            Order,
            reference=reference,
            user=self.request.user,
        )

        return (
            order.status_history
            .all()
            .order_by(
                "created_at"
            )
        )
    




class AdminOrderListAPIView(
    generics.ListAPIView
):

    serializer_class = (
        OrderListSerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsPlatformAdmin,
    ]

    queryset = (
        Order.objects
        .all()
        .order_by(
            "-created_at"
        )
    )

    filterset_class = (
        OrderFilter
    )

    filter_backends = [
        DjangoFilterBackend,
    ]






class AdminOrderDetailAPIView(
    generics.RetrieveAPIView
):

    serializer_class = (
        OrderDetailSerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsPlatformAdmin,
    ]

    queryset = (
        Order.objects
        .all()
        .prefetch_related(
            "items"
        )
    )

    lookup_field = (
        "reference"
    )





class AdminOrderStatusAPIView(
    generics.GenericAPIView
):

    serializer_class = (
        AdminOrderStatusSerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsPlatformAdmin,
    ]

    def patch(
        self,
        request,
        reference,
    ):

        serializer = (
            self.get_serializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        order = get_object_or_404(
            Order,
            reference=reference,
        )

        OrderService.update_status(
            order=order,
            new_status=serializer.validated_data[
                "status"
            ],
            changed_by=request.user,
            comment=serializer.validated_data.get(
                "comment",
                "",
            ),
        )

        order.refresh_from_db()

        return Response(
            OrderDetailSerializer(
                order
            ).data
        )