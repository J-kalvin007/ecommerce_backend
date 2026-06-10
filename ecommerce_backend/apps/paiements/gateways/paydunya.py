"""
Gateway d'intégration avec l'API PayDunya.

Implémente le design pattern Strategy pour être interchangeable.
"""
import json
import logging
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from requests.exceptions import RequestException

from ..exceptions import PaymentGatewayError

logger = logging.getLogger(__name__)

class BaseGateway:
    """Interface abstraite pour les fournisseurs de paiement."""

    def initiate_payment(self, amount: Decimal, phone_number: str, description: str, reference: str = None) -> dict[str, Any]:
        raise NotImplementedError

    def verify_payment(self, token: str) -> dict[str, Any]:
        raise NotImplementedError

    def request_payout(self, amount: Decimal, phone_number: str, description: str) -> dict[str, Any]:
        raise NotImplementedError


class PayDunyaGateway(BaseGateway):
    """
    Implémentation concrète pour PayDunya.

    Utilise les clés configurées dans settings :
    - PAYDUNYA_API_KEY
    - PAYDUNYA_API_SECRET
    - PAYDUNYA_MERCHANT_ID (optionnel)
    - PAYDUNYA_BASE_URL (par défaut https://paydunya.com/api/v1)
    """

    def __init__(self):
        self.api_key = settings.PAYDUNYA_API_KEY
        self.api_secret = settings.PAYDUNYA_API_SECRET
        self.merchant_id = getattr(settings, "PAYDUNYA_MERCHANT_ID", None)
        self.base_url = getattr(
            settings,
            "PAYDUNYA_BASE_URL",
            "https://paydunya.com/api/v1",
        )
        self.session = requests.Session()
        self.session.auth = (self.api_key, self.api_secret)

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict[str, Any]:
        """Exécute un appel HTTP vers PayDunya et gère les erreurs."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(method, url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error("PayDunya API request failed: %s", e)
            raise PaymentGatewayError(f"Erreur de communication avec PayDunya : {e}") from e
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON response from PayDunya: %s", e)
            raise PaymentGatewayError("Réponse invalide de PayDunya.") from e

    def initiate_payment(
        self,
        amount: Decimal,
        phone_number: str,
        description: str,
        reference: str = None,
    ) -> dict[str, Any]:
        """
        Initie un paiement Mobile Money ou carte via PayDunya.

        Returns:
            dict avec les clés 'token' et 'redirect_url'.
        """
        payload = {
            "amount": str(amount),
            "phone_number": phone_number,
            "description": description,
        }
        if reference:
            payload["invoice_token"] = reference

        result = self._request("POST", "checkout-invoice/create", payload)
        if not result.get("token"):
            raise PaymentGatewayError("Token non retourné par PayDunya.")
        redirect_url = result.get("response_url") or result.get("redirect_url")
        if not redirect_url:
            raise PaymentGatewayError("URL de redirection manquante.")
        return {"token": result["token"], "redirect_url": redirect_url}

    def verify_payment(self, token: str) -> dict[str, Any]:
        """
        Vérifie le statut d'une transaction auprès de PayDunya.

        Returns:
            dict contenant au moins les clés 'status' et 'amount'.
        """
        result = self._request("GET", f"checkout-invoice/confirm/{token}")
        status_mapping = {
            "completed": "completed",
            "pending": "pending",
            "cancelled": "cancelled",
        }
        return {
            "status": status_mapping.get(result.get("status"), result.get("status")),
            "amount": result.get("amount"),
            "raw": result,
        }

    def request_payout(
        self, amount: Decimal, phone_number: str, description: str
    ) -> dict[str, Any]:
        """
        Effectue un transfert d'argent vers un numéro mobile money.

        Note: endpoint hypothétique basé sur la documentation PayDunya.
        """
        payload = {
            "amount": str(amount),
            "phone_number": phone_number,
            "description": description,
        }
        result = self._request("POST", "payout/create", payload)
        if not result.get("token"):
            raise PaymentGatewayError("Payout non initié (token manquant).")
        return {"token": result["token"]}