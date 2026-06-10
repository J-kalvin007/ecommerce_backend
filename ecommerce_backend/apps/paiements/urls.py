from django.urls import path

from .views import (
    WalletBalanceView,
    WalletDepositView,
    WalletPayView,
    WalletTransactionsView,
    PaymentInitiateView,
    PayDunyaWebhookView,
    AdminWithdrawView,
)

urlpatterns = [
    path(
        "wallet/",
        WalletBalanceView.as_view(),
        name="wallet-balance",
    ),
    path(
        "wallet/deposit/",
        WalletDepositView.as_view(),
        name="wallet-deposit",
    ),
    path(
        "wallet/pay/",
        WalletPayView.as_view(),
        name="wallet-pay",
    ),
    path(
        "wallet/transactions/",
        WalletTransactionsView.as_view(),
        name="wallet-transactions",
    ),
    path(
        "initiate/",
        PaymentInitiateView.as_view(),
        name="payment-initiate",
    ),
    path(
        "webhook/paydunya/",
        PayDunyaWebhookView.as_view(),
        name="paydunya-webhook",
    ),
    path(
        "admin/withdraw/",
        AdminWithdrawView.as_view(),
        name="admin-withdraw",
    ),
]