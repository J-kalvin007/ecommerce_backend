"""
Gateway d'intégration avec l'API PayDunya.

Architecture :
- BaseGateway   : interface abstraite (Strategy pattern)
- PayDunyaGateway : implémentation concrète pour PayDunya

Documentation API PayDunya v1 :
https://paydunya.com/developers

Authentification :
L'API PayDunya utilise 4 headers custom (PAS Basic Auth) :
    PAYDUNYA-MASTER-KEY   → Master Key (Principale Key du dashboard)
    PAYDUNYA-PUBLIC-KEY   → Public Key
    PAYDUNYA-PRIVATE-KEY  → Private Key
    PAYDUNYA-TOKEN        → Token IPN secret

Mode test : les clés commencent par "test_public_" / "test_private_"
Mode live : les clés commencent par "live_public_" / "live_private_"
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
    """Interface abstraite pour les fournisseurs de paiement (Strategy pattern)."""

    def initiate_payment(
        self, amount: Decimal, phone_number: str, description: str, reference: str = None
    ) -> dict[str, Any]:
        raise NotImplementedError

    def verify_payment(self, token: str) -> dict[str, Any]:
        raise NotImplementedError

    def request_payout(
        self, amount: Decimal, phone_number: str, description: str
    ) -> dict[str, Any]:
        raise NotImplementedError


class PayDunyaGateway(BaseGateway):
    """
    Implémentation concrète pour PayDunya v1.

    Lit les clés depuis les settings Django (injectés via .envs/.local/.payDunya) :
        settings.PAYDUNYA_MASTER_KEY   ← PAYDUNYA_PINCIPALE_KEY
        settings.PAYDUNYA_PUBLIC_KEY   ← PAYDUNYA_PUBLIC_KEY
        settings.PAYDUNYA_PRIVATE_KEY  ← PAYDUNYA_PRIVATE_KEY
        settings.PAYDUNYA_TOKEN        ← PAYDUNYA_TOKEN
        settings.PAYDUNYA_BASE_URL     ← (optionnel, défaut http://192.168.1.68:8000/api/v1)

    Les 4 clés sont transmises comme headers HTTP à chaque requête.
    """

    # URL de base officielle de l'API PayDunya
    DEFAULT_BASE_URL = "http://192.168.1.68:8000/api/v1"

    def __init__(self):
        self.master_key  = getattr(settings, "PAYDUNYA_MASTER_KEY",  "")
        self.public_key  = getattr(settings, "PAYDUNYA_PUBLIC_KEY",  "")
        self.private_key = getattr(settings, "PAYDUNYA_PRIVATE_KEY", "")
        self.token       = getattr(settings, "PAYDUNYA_TOKEN",        "")
        self.base_url    = getattr(settings, "PAYDUNYA_BASE_URL", self.DEFAULT_BASE_URL).rstrip("/")
        self.mode        = getattr(settings, "PAYDUNYA_MODE", "test")

        # Validation des clés au démarrage (log d'avertissement, pas d'exception)
        if not all([self.master_key, self.public_key, self.private_key, self.token]):
            logger.warning(
                "PayDunya : une ou plusieurs clés API manquantes. "
                "Vérifiez .envs/.local/.payDunya (PAYDUNYA_PINCIPALE_KEY, "
                "PAYDUNYA_PUBLIC_KEY, PAYDUNYA_PRIVATE_KEY, PAYDUNYA_TOKEN)."
            )

        # Session HTTP réutilisable avec headers d'authentification injectés
        self.session = requests.Session()
        self.session.headers.update(self._auth_headers())

    def _auth_headers(self) -> dict[str, str]:
        """
        Construit les 4 headers d'authentification requis par l'API PayDunya.

        Returns:
            dict: headers à inclure dans chaque requête HTTP.
        """
        return {
            "PAYDUNYA-MASTER-KEY":  self.master_key,
            "PAYDUNYA-PUBLIC-KEY":  self.public_key,
            "PAYDUNYA-PRIVATE-KEY": self.private_key,
            "PAYDUNYA-TOKEN":       self.token,
            "Content-Type":         "application/json",
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict[str, Any]:
        """
        Exécute un appel HTTP vers l'API PayDunya.

        Args:
            method: verbe HTTP ("GET", "POST", etc.)
            endpoint: chemin relatif (ex: "checkout-invoice/create")
            data: payload JSON (optionnel)

        Returns:
            dict: réponse JSON parsée.

        Raises:
            PaymentGatewayError: en cas d'erreur réseau ou de réponse invalide.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.debug("[PayDunya] %s %s | mode=%s", method, url, self.mode)
        try:
            response = self.session.request(
                method,
                url,
                json=data,
                timeout=30,
            )
            logger.debug("[PayDunya] HTTP %s — %s", response.status_code, response.text[:200])
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error("[PayDunya] Erreur requête : %s", e)
            raise PaymentGatewayError(f"Erreur de communication avec PayDunya : {e}") from e
        except json.JSONDecodeError as e:
            logger.error("[PayDunya] Réponse JSON invalide : %s", e)
            raise PaymentGatewayError("Réponse invalide reçue de PayDunya.") from e

    def initiate_payment(
        self,
        amount: Decimal,
        phone_number: str,
        description: str,
        reference: str = None,
    ) -> dict[str, Any]:
        """
        Initie un paiement Mobile Money ou carte via PayDunya.

        L'endpoint PayDunya crée une "checkout invoice" et retourne
        un token + une URL de redirection.

        Args:
            amount: montant en FCFA.
            phone_number: numéro Mobile Money du payeur.
            description: libellé de la transaction.
            reference: référence interne optionnelle.

        Returns:
            dict avec les clés 'token' (str) et 'redirect_url' (str).

        Raises:
            PaymentGatewayError: si la réponse ne contient pas le token ou l'URL.
        """
        payload = {
            "invoice": {
                "total_amount": int(amount),  # PayDunya attend un entier (FCFA)
                "description": description,
            },
            "store": {
                "name": getattr(settings, "SITE_NAME", "Ecommerce"),
            },
            "actions": {
                "cancel_url": getattr(settings, "PAYDUNYA_CANCEL_URL", ""),
                "return_url": getattr(settings, "PAYDUNYA_RETURN_URL", ""),
                "callback_url": getattr(settings, "PAYDUNYA_CALLBACK_URL", ""),
            },
            "custom_data": {
                "phone_number": phone_number,
            },
        }
        if reference:
            payload["custom_data"]["internal_reference"] = reference

        result = self._request("POST", "checkout-invoice/create", payload)

        # Vérifier le succès selon la doc PayDunya
        if not result.get("response_code") == "00" and not result.get("token"):
            raise PaymentGatewayError(
                f"PayDunya a refusé la création de facture : {result.get('response_text', result)}"
            )

        token = result.get("token")
        if not token:
            raise PaymentGatewayError("Token non retourné par PayDunya.")

        redirect_url = (
            result.get("response_url")
            or result.get("redirect_url")
            or result.get("checkout_url")
        )
        if not redirect_url:
            raise PaymentGatewayError("URL de redirection manquante dans la réponse PayDunya.")

        logger.info("[PayDunya] Facture créée — token=%s | url=%s", token, redirect_url)
        return {"token": token, "redirect_url": redirect_url}

    def verify_payment(self, token: str) -> dict[str, Any]:
        """
        Vérifie le statut d'une transaction auprès de PayDunya.

        Args:
            token: le token de la transaction à vérifier.

        Returns:
            dict avec les clés :
                'status' : "completed" | "pending" | "cancelled" | "failed"
                'amount' : montant
                'raw'    : réponse brute complète de l'API

        Raises:
            PaymentGatewayError: en cas d'erreur réseau.
        """
        result = self._request("GET", f"checkout-invoice/confirm/{token}")

        # Normalisation du statut PayDunya vers nos statuts internes
        raw_status = result.get("status", "")
        status_map = {
            "completed": "completed",
            "pending":   "pending",
            "cancelled": "cancelled",
            "failed":    "failed",
        }
        normalized_status = status_map.get(raw_status.lower(), raw_status)

        logger.info(
            "[PayDunya] Vérification token=%s → statut=%s", token, normalized_status
        )
        return {
            "status": normalized_status,
            "amount": result.get("invoice", {}).get("total_amount") or result.get("amount"),
            "raw": result,
        }

    def request_payout(
        self, amount: Decimal, phone_number: str, description: str
    ) -> dict[str, Any]:
        """
        Effectue un transfert d'argent (payout) vers un numéro Mobile Money.

        Note : endpoint basé sur la documentation PayDunya Disburse/Payout API.
        Vérifiez que votre compte PayDunya dispose des droits de payout.

        Args:
            amount: montant à transférer (FCFA).
            phone_number: numéro destinataire.
            description: motif du transfert.

        Returns:
            dict avec la clé 'token'.

        Raises:
            PaymentGatewayError: si le payout échoue.
        """
        payload = {
            "amount": int(amount),
            "phone_number": phone_number,
            "description": description,
        }
        result = self._request("POST", "disburse/get-started", payload)

        if not result.get("token"):
            raise PaymentGatewayError(
                f"Payout non initié — réponse PayDunya : {result}"
            )

        logger.info(
            "[PayDunya] Payout initié — token=%s | montant=%s | tel=%s",
            result["token"], amount, phone_number,
        )
        return {"token": result["token"]}