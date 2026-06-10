"""
Vues DRF pour le module de paiement.

Zéro logique métier : toute la logique est déléguée aux services.
"""
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsPlatformAdmin
from .exceptions import (
    InsufficientBalanceError,
    PaymentGatewayError,
    WalletInactiveError,
)
from .models import WalletTransaction, Payment
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
    DepositSerializer,
    WalletPaySerializer,
    InitiatePaymentSerializer,
    PaymentSerializer,
    AdminWithdrawSerializer,
)
from .services import PaymentService, WalletService


class WalletBalanceView(RetrieveAPIView):
    """GET /api/v1/payments/wallet/ - Solde et statut du wallet de l'utilisateur."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return WalletService.get_wallet(self.request.user)

    serializer_class = WalletSerializer


class WalletTransactionsView(ListAPIView):
    """GET /api/v1/payments/wallet/transactions/ - Historique des transactions."""

    permission_classes = [IsAuthenticated]
    serializer_class = WalletTransactionSerializer

    def get_queryset(self):
        wallet = WalletService.get_wallet(self.request.user)
        return wallet.transactions.select_related("order").order_by("-created_at")


class WalletDepositView(APIView):
    """POST /api/v1/payments/wallet/deposit/ - Initier une recharge de wallet via PayDunya."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_service = PaymentService()
        try:
            payment, redirect_url = payment_service.initiate_wallet_topup(
                user=request.user,
                amount=serializer.validated_data["amount"],
                phone_number=serializer.validated_data["phone_number"],
            )
            return Response(
                {
                    "payment_id": payment.id,
                    "redirect_url": redirect_url,
                    "token": payment.reference_externe,
                },
                status=status.HTTP_201_CREATED,
            )
        except WalletInactiveError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PaymentGatewayError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class WalletPayView(APIView):
    """POST /api/v1/payments/wallet/pay/ - Payer une commande avec le wallet."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletPaySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data["order_id"]
        from apps.commandes.models import Order

        order = Order.objects.get(pk=order_id)
        payment_service = PaymentService()
        try:
            payment = payment_service.process_wallet_payment(
                user=request.user, order=order
            )
            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_200_OK,
            )
        except InsufficientBalanceError as e:
            return Response({"detail": str(e)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except WalletInactiveError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentInitiateView(APIView):
    """POST /api/v1/payments/initiate/ - Paiement direct PayDunya (authentifié ou non)."""

    permission_classes = []  # AllowAny pour les visiteurs anonymes

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_service = PaymentService()
        data = serializer.validated_data
        order = None
        if data.get("order_id"):
            from apps.commandes.models import Order

            order = Order.objects.get(pk=data["order_id"])
        try:
            payment, redirect_url = payment_service.initiate_direct_payment(
                order=order,
                phone_number=data["phone_number"],
                user=request.user if request.user.is_authenticated else None,
            )
            return Response(
                {
                    "payment_id": payment.id,
                    "redirect_url": redirect_url,
                    "token": payment.reference_externe,
                },
                status=status.HTTP_201_CREATED,
            )
        except PaymentGatewayError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class PayDunyaWebhookView(APIView):
    """POST /api/v1/payments/webhook/paydunya/ - Callback PayDunya (public)."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                {"detail": "Token manquant."}, status=status.HTTP_400_BAD_REQUEST
            )
        payment_service = PaymentService()
        try:
            payment = payment_service.handle_webhook(token, request.data)
            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_200_OK,
            )
        except PaymentGatewayError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response(
                {"detail": "Erreur interne du webhook."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminWithdrawView(APIView):
    """POST /api/v1/payments/admin/withdraw/ - Retrait de fonds vers un numéro mobile money (admin)."""

    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        serializer = AdminWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_service = PaymentService()
        try:
            payment = payment_service.admin_withdraw(
                amount=serializer.validated_data["amount"],
                phone_number=serializer.validated_data["phone_number"],
                description=serializer.validated_data.get("description", ""),
            )
            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_200_OK,
            )
        except PaymentGatewayError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)