

from allauth.account.signals import email_confirmed
from django.dispatch import receiver


@receiver(email_confirmed)
def mark_user_verified(request, email_address, **kwargs):
    user = email_address.user

    if not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])