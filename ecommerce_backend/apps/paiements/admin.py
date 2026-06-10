from django.contrib import admin
from django.db import transaction
from django.utils.html import format_html

from .models import Payment, PayDunyaWebhookLog, Wallet, WalletTransaction
from .services import PaymentService


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user_email", "balance", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("balance", "created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Utilisateur"


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "wallet_user", "transaction_type", "amount", "status", "created_at")
    list_filter = ("transaction_type", "status", "created_at")
    search_fields = ("reference", "wallet__user__email")
    readonly_fields = ("wallet", "order", "metadata", "created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("wallet__user", "order")

    def wallet_user(self, obj):
        return obj.wallet.user.email
    wallet_user.short_description = "Propriétaire"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "payment_type", "amount", "status", "order_ref", "created_at")
    list_filter = ("provider", "payment_type", "status", "created_at")
    search_fields = ("reference_externe", "order__reference")
    readonly_fields = ("webhook_token", "metadata", "created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order")

    def order_ref(self, obj):
        if obj.order:
            return obj.order.reference
        return "-"
    order_ref.short_description = "Commande"

    actions = ["manual_withdraw_action"]

    @transaction.atomic
    def manual_withdraw_action(self, request, queryset):
        """
        Action personnalisée pour déclencher un retrait vers PayDunya
        à partir d'un paiement sélectionné (uniquement ceux en attente).
        """
        service = PaymentService()
        count = 0
        for payment in queryset.filter(payment_type="admin_withdraw", status="pending"):
            try:
                # relancer le payout (utilisation du numéro de téléphone stocké en metadata)
                phone = payment.metadata.get("phone_number")
                if phone:
                    service.admin_withdraw(payment.amount, phone)
                    count += 1
            except Exception as e:
                self.message_user(request, f"Échec pour {payment.id}: {e}", level="ERROR")
        self.message_user(request, f"{count} retrait(s) effectué(s).")

    manual_withdraw_action.short_description = "Effectuer le retrait PayDunya sélectionné"


@admin.register(PayDunyaWebhookLog)
class PayDunyaWebhookLogAdmin(admin.ModelAdmin):
    list_display = ("token", "status_traitement", "created_at")
    list_filter = ("status_traitement", "created_at")
    search_fields = ("token",)
    readonly_fields = ("payload",)