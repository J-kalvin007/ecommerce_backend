"""
Couche de services métier pour le module de fidélisation.

LoyaltyService orchestre :
- L'attribution de points après livraison
- Le cashback automatique (crédit wallet)
- La dépense de points
- L'expiration des points
- Les bonus (parrainage, anniversaire)
"""
import logging
import datetime
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import LoyaltyTier, LoyaltyProfile, LoyaltyEvent, TierChangeLog

logger = logging.getLogger(__name__)

# ─── Constantes (configurables dans settings) ────────────────────────────
POINT_VALUE = Decimal(getattr(settings, "LOYALTY_POINT_VALUE", "100.00"))
POINTS_EXPIRY_DAYS = getattr(settings, "LOYALTY_POINTS_EXPIRY_DAYS", 365)
REFERRAL_BONUS_POINTS = getattr(settings, "LOYALTY_REFERRAL_BONUS_POINTS", 200)
BIRTHDAY_BONUS_POINTS = getattr(settings, "LOYALTY_BIRTHDAY_BONUS_POINTS", 500)
FIRST_PURCHASE_BONUS_POINTS = getattr(settings, "LOYALTY_FIRST_PURCHASE_BONUS_POINTS", 100)


class LoyaltyService:
    """
    Moteur de fidélisation : points, cashback, paliers.

    Toutes les opérations financières (cashback) passent par WalletService
    pour garantir la cohérence du journal WalletTransaction.
    """

    @staticmethod
    @transaction.atomic
    def award_points(user, order) -> Optional[LoyaltyEvent]:
        """
        Attribue des points de fidélité après une commande livrée.

        Calcule les points de base (total commande × multiplicateur palier),
        ajoute un bonus premier achat si applicable.

        IDEMPOTENCE : vérifie si un LoyaltyEvent reason=PURCHASE existe
        déjà pour cette commande avant tout traitement.

        Args:
            user: Utilisateur propriétaire de la commande.
            order: Commande livrée (Order instance).

        Returns:
            LoyaltyEvent créé, ou None si déjà traité.
        """
        # Anti-double-traitement
        if LoyaltyEvent.objects.filter(
            user=user, order=order, reason=LoyaltyEvent.Reason.PURCHASE
        ).exists():
            logger.info(
                "Points déjà attribués pour la commande %s — ignoré.",
                order.reference,
            )
            return None

        profile = LoyaltyProfile.objects.select_for_update().get(user=user)
        tier = profile.tier or LoyaltyTier.objects.filter(is_default=True).first()

        # Points de base
        base_points = int(order.total_final)
        multiplier = tier.points_multiplier if tier else Decimal("1.00")
        points_awarded = int(base_points * multiplier)

        events_created = []

        # Bonus premier achat
        is_first_order = not LoyaltyEvent.objects.filter(
            user=user, reason=LoyaltyEvent.Reason.PURCHASE
        ).exists()
        if is_first_order:
            points_awarded += FIRST_PURCHASE_BONUS_POINTS
            events_created.append(
                LoyaltyEvent.objects.create(
                    user=user,
                    points_delta=FIRST_PURCHASE_BONUS_POINTS,
                    new_points_balance_after=profile.points_balance + points_awarded,
                    reason=LoyaltyEvent.Reason.FIRST_PURCHASE,
                    order=order,
                    description=f"Bonus premier achat : +{FIRST_PURCHASE_BONUS_POINTS} pts",
                )
            )

        # Mettre à jour le profil
        profile.points_balance = F("points_balance") + points_awarded
        profile.total_points_earned = F("total_points_earned") + points_awarded
        profile.total_solde = F("total_solde") + order.total_final
        profile.save(update_fields=["points_balance", "total_points_earned", "total_solde", "updated_at"])
        profile.refresh_from_db()

        # Event principal d'achat
        event = LoyaltyEvent.objects.create(
            user=user,
            points_delta=points_awarded,
            new_points_balance_after=profile.points_balance,
            reason=LoyaltyEvent.Reason.PURCHASE,
            order=order,
            expires_at=timezone.now() + datetime.timedelta(days=POINTS_EXPIRY_DAYS),
            description=f"Points gagnés sur commande {order.reference} (×{multiplier})",
        )

        # Recalculer le palier
        profile.recalculate_tier()

        logger.info(
            "Points attribués à %s : +%d pts (total: %d)",
            user.email,
            points_awarded,
            profile.points_balance,
        )
        return event

    @staticmethod
    @transaction.atomic
    def award_cashback(user, order) -> Optional[Decimal]:
        """
        Crédite le cashback dans le wallet après une commande livrée.

        IDEMPOTENCE : vérifie si un WalletTransaction reason=CASHBACK existe
        déjà pour cette commande.

        Args:
            user: Utilisateur.
            order: Commande livrée.

        Returns:
            Decimal: Montant du cashback crédité, ou None si déjà traité.
        """
        from apps.paiements.models import WalletTransaction

        # Anti-double-traitement
        if WalletTransaction.objects.filter(
            wallet__user=user,
            reference=f"CB-{order.reference}",
            transaction_type=WalletTransaction.Type.CASHBACK,
        ).exists():
            logger.info(
                "Cashback déjà crédité pour la commande %s — ignoré.",
                order.reference,
            )
            return None

        profile = LoyaltyProfile.objects.get(user=user)
        tier = profile.tier or LoyaltyTier.objects.filter(is_default=True).first()

        if not tier or tier.cashback_percent == 0:
            return Decimal("0.00")

        cashback = (order.total_final * tier.cashback_percent / 100).quantize(
            Decimal("0.01")
        )

        if cashback <= 0:
            return Decimal("0.00")

        # Créditer le wallet via WalletService (NE PAS toucher Wallet.balance directement)
        from apps.paiements.services import WalletService

        wallet = WalletService.get_wallet(user)
        WalletService.credit(
            wallet=wallet,
            amount=cashback,
            reference=f"CB-{order.reference}",
            metadata={
                "order_reference": order.reference,
                "cashback_percent": str(tier.cashback_percent),
            },
        )

        # Créer l'événement de fidélité
        LoyaltyEvent.objects.create(
            user=user,
            points_delta=0,  # Le cashback n'affecte pas les points
            new_points_balance_after=profile.points_balance,
            reason=LoyaltyEvent.Reason.PURCHASE, # Le cashback est lié à l'achat
            order=order,
            description=f"Cashback {tier.cashback_percent}% : +{cashback} FCFA",
        )

        logger.info(
            "Cashback crédité à %s : +%s FCFA",
            user.email,
            cashback,
        )
        return cashback

    @staticmethod
    @transaction.atomic
    def redeem_points(user, order, points_to_spend: int) -> Decimal:
        """
        Dépense des points de fidélité pour obtenir une réduction.

        Utilise select_for_update() sur le profil pour éviter les
        soldes négatifs en cas de requêtes concurrentes.

        Args:
            user: Utilisateur.
            order: Commande en cours.
            points_to_spend: Nombre de points à dépenser.

        Returns:
            Decimal: Montant de réduction obtenu.

        Raises:
            ValueError: Si points_to_spend > points_balance.
        """
        profile = LoyaltyProfile.objects.select_for_update().get(user=user)

        if points_to_spend <= 0:
            raise ValueError("Le nombre de points doit être positif.")

        if points_to_spend > profile.points_balance:
            raise ValueError(
                f"Solde insuffisant. Vous avez {profile.points_balance} pts, "
                f"vous demandez {points_to_spend} pts."
            )

        # Calculer la réduction
        discount = (Decimal(points_to_spend) * POINT_VALUE / 100).quantize(
            Decimal("0.01")
        )

        # Décrémenter le solde
        profile.points_balance = F("points_balance") - points_to_spend
        profile.save(update_fields=["points_balance", "updated_at"])
        profile.refresh_from_db()

        # Créer l'événement
        LoyaltyEvent.objects.create(
            user=user,
            points_delta=-points_to_spend,
            new_points_balance_after=profile.points_balance,
            reason=LoyaltyEvent.Reason.ORDER_DISCOUNT,
            order=order,
            description=f"Dépense {points_to_spend} pts → réduction {discount} FCFA",
        )

        # Appliquer la réduction à la commande
        order.discount_amount = F("discount_amount") + discount
        order.total_final = F("total_final") - discount
        order.save(update_fields=["discount_amount", "total_final", "updated_at"])
        order.refresh_from_db()

        logger.info(
            "Points dépensés par %s : -%d pts → -%s FCFA",
            user.email,
            points_to_spend,
            discount,
        )
        return discount

    @staticmethod
    def expire_points():
        """
        Tâche planifiée : expire les points dont la date est dépassée.

        Pour chaque LoyaltyEvent reason=PURCHASE expiré et non déjà
        traité (points_delta > 0), crée un événement POINTS_EXPIRY
        et décrémente le solde.
        """
        from django.db.models import Sum

        now = timezone.now()
        expired_events = LoyaltyEvent.objects.filter(
            reason=LoyaltyEvent.Reason.PURCHASE,
            points_delta__gt=0,
            expires_at__isnull=False,
            expires_at__lt=now,
        )

        processed = 0
        for event in expired_events:
            with transaction.atomic():
                profile = LoyaltyProfile.objects.select_for_update().get(
                    user=event.user
                )
                # Vérifier que le solde est suffisant
                expire_amount = min(event.points_delta, profile.points_balance)
                if expire_amount <= 0:
                    continue

                profile.points_balance = F("points_balance") - expire_amount
                profile.save(update_fields=["points_balance", "updated_at"])
                profile.refresh_from_db()

                LoyaltyEvent.objects.create(
                    user=event.user,
                    points_delta=-expire_amount,
                    new_points_balance_after=profile.points_balance,
                    reason=LoyaltyEvent.Reason.POINTS_EXPIRY,
                    description=f"Expiration de {expire_amount} pts (commande du {event.created_at.date()})",
                )
                processed += 1

        logger.info("Expiration de points terminée : %d événements traités.", processed)
        return processed

    @staticmethod
    def award_referral_bonus(referrer_user, new_user):
        """
        Attribue un bonus de points au parrain lors du premier achat du filleul.

        Args:
            referrer_user: Le parrain.
            new_user: Le filleul qui vient de faire son premier achat.
        """
        with transaction.atomic():
            profile = LoyaltyProfile.objects.select_for_update().get(
                user=referrer_user
            )
            profile.points_balance = F("points_balance") + REFERRAL_BONUS_POINTS
            profile.total_points_earned = F("total_points_earned") + REFERRAL_BONUS_POINTS
            profile.save(update_fields=["points_balance", "total_points_earned", "updated_at"])
            profile.refresh_from_db()

            LoyaltyEvent.objects.create(
                user=referrer_user,
                points_delta=REFERRAL_BONUS_POINTS,
                new_points_balance_after=profile.points_balance,
                reason=LoyaltyEvent.Reason.REFERRAL_BONUS,
                description=f"Bonus parrainage : {new_user.email} a fait son premier achat.",
            )
            profile.recalculate_tier()

    @staticmethod
    def award_birthday_bonus():
        """
        Tâche planifiée quotidienne : attribue un bonus d'anniversaire
        aux utilisateurs dont c'est l'anniversaire aujourd'hui.
        """
        today = timezone.now().date()
        profiles = LoyaltyProfile.objects.filter(
            birth_date__month=today.month,
            birth_date__day=today.day,
        ).select_related("user")

        count = 0
        for profile in profiles:
            with transaction.atomic():
                profile = LoyaltyProfile.objects.select_for_update().get(
                    pk=profile.pk
                )
                profile.points_balance = F("points_balance") + BIRTHDAY_BONUS_POINTS
                profile.total_points_earned = F("total_points_earned") + BIRTHDAY_BONUS_POINTS
                profile.save(update_fields=["points_balance", "total_points_earned", "updated_at"])
                profile.refresh_from_db()

                LoyaltyEvent.objects.create(
                    user=profile.user,
                    points_delta=BIRTHDAY_BONUS_POINTS,
                    new_points_balance_after=profile.points_balance,
                    reason=LoyaltyEvent.Reason.BIRTHDAY_BONUS,
                    description=f"🎂 Joyeux anniversaire ! +{BIRTHDAY_BONUS_POINTS} pts",
                )
                profile.recalculate_tier()
                count += 1

        logger.info("Bonus anniversaire : %d utilisateur(s) récompensé(s).", count)
        return count