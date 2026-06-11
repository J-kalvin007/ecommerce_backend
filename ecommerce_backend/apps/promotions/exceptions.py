


"""Exceptions métier pour le module promotions."""


class PromoCodeError(Exception):
    """Exception de base pour les erreurs de code promo."""
    default_message = "Erreur code promo."
    default_code = "promo_code_error"

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class InvalidPromoCodeError(PromoCodeError):
    """Le code promo n'existe pas ou n'est pas valide."""
    default_message = "Code promo invalide."
    default_code = "invalid_promo_code"


class PromoExpiredError(PromoCodeError):
    """Le code promo a expiré."""
    default_message = "Ce code promo a expiré."
    default_code = "promo_expired"


class PromoQuotaExceededError(PromoCodeError):
    """Le quota d'utilisation global du code promo est atteint."""
    default_message = "Quota d'utilisation du code promo atteint."
    default_code = "promo_quota_exceeded"


class PromoUserQuotaExceededError(PromoCodeError):
    """L'utilisateur a déjà utilisé ce code promo le nombre maximum autorisé."""
    default_message = "Vous avez déjà utilisé ce code promo le nombre maximum de fois."
    default_code = "promo_user_quota_exceeded"


class PromoTierRestrictionError(PromoCodeError):
    """Le palier de fidélité de l'utilisateur ne permet pas d'utiliser ce code."""
    default_message = "Votre niveau de fidélité ne permet pas d'utiliser ce code promo."
    default_code = "promo_tier_restricted"


class PromoMinOrderError(PromoCodeError):
    """Le montant minimum de commande n'est pas atteint."""
    default_message = "Le montant minimum de commande n'est pas atteint pour ce code promo."
    default_code = "promo_min_order"


class FlashSaleError(Exception):
    """Exception de base pour les erreurs de flash sale."""
    pass