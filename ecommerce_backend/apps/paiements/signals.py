"""
Signaux métier pour le module de paiement.
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Wallet


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet_on_user_creation(sender, instance, created, **kwargs):
    """
    Crée automatiquement un Wallet lors de la création d'un nouvel utilisateur.
    """
    if created and not hasattr(instance, "wallet"):
        Wallet.objects.create(user=instance)