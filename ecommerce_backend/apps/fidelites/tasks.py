


"""
Tâches planifiées Celery pour le module de fidélisation.

- expire_points : quotidienne, expire les points dépassés
- birthday_bonus : quotidienne, attribue les bonus d'anniversaire
"""
from celery import shared_task
from celery.utils.log import get_task_logger

from .services import LoyaltyService

logger = get_task_logger(__name__)


@shared_task(name="loyalty.expire_points")
def expire_points_task():
    """
    Tâche planifiée : expire les points de fidélité dont la date est dépassée.

    Planification recommandée : quotidienne, ex. 02:00 UTC.
    """
    logger.info("Démarrage de la tâche d'expiration des points...")
    try:
        processed = LoyaltyService.expire_points()
        logger.info(f"Expiration terminée : {processed} événements traités.")
        return processed
    except Exception as e:
        logger.error(f"Erreur lors de l'expiration des points : {e}")
        raise


@shared_task(name="loyalty.birthday_bonus")
def birthday_bonus_task():
    """
    Tâche planifiée : attribue les bonus d'anniversaire.

    Planification recommandée : quotidienne, ex. 08:00 UTC.
    """
    logger.info("Démarrage de la tâche de bonus d'anniversaire...")
    try:
        count = LoyaltyService.award_birthday_bonus()
        logger.info(f"Bonus anniversaire : {count} utilisateur(s) récompensé(s).")
        return count
    except Exception as e:
        logger.error(f"Erreur lors du bonus anniversaire : {e}")
        raise