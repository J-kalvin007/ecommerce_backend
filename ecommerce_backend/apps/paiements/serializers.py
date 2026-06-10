


"""
Serializers DRF avec validation métier pour les endpoints de paiement.
"""
from decimal import Decimal
from rest_framework import serializers

from apps.commandes.models import Order
from .models import Wallet, WalletTransaction, Payment
from .services import WalletService


class WalletSerializer(serializers.ModelSerializer):
    """Affichage du solde et statut."""

    class Meta:
        model = Wallet
        fields = ("id", "balance", "status", "created_at", "updated_at")
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Historique des transactions."""

    class Meta:
        model = WalletTransaction
        fields = (
            "id",
            "transaction_type",
            "amount",
            "reference",
            "order",
            "status",
            "created_at",
        )
        read_only_fields = fields


class DepositSerializer(serializers.Serializer):
    """Initiation d'une recharge de wallet."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    phone_number = serializers.CharField(max_length=30)

    def validate_phone_number(self, value):
        if not value.startswith("+"):
            raise serializers.ValidationError("Le numéro doit être au format international (+221...).")
        return value


class WalletPaySerializer(serializers.Serializer):
    """Paiement d'une commande via le wallet."""

    order_id = serializers.UUIDField()

    def validate_order_id(self, value):
        try:
            order = Order.objects.get(pk=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Commande introuvable.")
        if order.status not in ("pending_payment",):
            raise serializers.ValidationError("Cette commande ne peut plus être payée.")
        if order.user != self.context["request"].user:
            raise serializers.ValidationError("Vous ne pouvez payer que vos propres commandes.")
        return value


class InitiatePaymentSerializer(serializers.Serializer):
    """Paiement direct PayDunya (avec ou sans commande existante)."""

    order_id = serializers.UUIDField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    phone_number = serializers.CharField(max_length=30)

    def validate(self, data):
        if data.get("order_id"):
            try:
                order = Order.objects.get(pk=data["order_id"])
                if order.total_final != data["amount"]:
                    raise serializers.ValidationError(
                        "Le montant ne correspond pas au total de la commande."
                    )
            except Order.DoesNotExist:
                raise serializers.ValidationError("Commande introuvable.")
        return data

    def validate_phone_number(self, value):
        if not value.startswith("+"):
            raise serializers.ValidationError("Format international requis (+221...).")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """Détail d'un paiement."""

    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "provider",
            "payment_type",
            "amount",
            "status",
            "reference_externe",
            "created_at",
        )
        read_only_fields = fields


class AdminWithdrawSerializer(serializers.Serializer):
    """Demande de retrait administrateur."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1.00"))
    phone_number = serializers.CharField(max_length=30)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)