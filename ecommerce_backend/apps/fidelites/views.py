"""
Vues DRF pour le module de fidélisation.

Endpoints :
- GET  /me/ : profil loyalty de l'utilisateur connecté
- GET  /tiers/ : tous les paliers (public)
- POST /points/redeem/ : dépenser des points
- GET  /events/ : journal des événements
- GET  /referral/ : code de parrainage + stats
- Admin : gestion des profils, ajustement manuel
"""
from django.db import models
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsPlatformAdmin
from .models import LoyaltyTier, LoyaltyProfile, LoyaltyEvent
from .serializers import (
    TierSerializer,
    LoyaltyProfileSerializer,
    LoyaltyEventSerializer,
    RedeemPointsSerializer,
    AdminAdjustPointsSerializer,
)
from .services import LoyaltyService


class MyLoyaltyProfileView(APIView):
    """
    GET /api/v1/loyalty/me/
    Profil de fidélité complet de l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = LoyaltyProfile.objects.select_related("tier").get(
                user=request.user
            )
        except LoyaltyProfile.DoesNotExist:
            return Response(
                {"detail": "Profil de fidélité introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LoyaltyProfileSerializer(profile)
        return Response(serializer.data)


class TiersListView(APIView):
    """
    GET /api/v1/loyalty/tiers/
    Liste de tous les paliers avec leurs avantages (public).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        tiers = LoyaltyTier.objects.all().order_by("min_points")
        serializer = TierSerializer(tiers, many=True)
        return Response(serializer.data)


class RedeemPointsView(APIView):
    """
    POST /api/v1/loyalty/points/redeem/
    Dépenser des points de fidélité sur une commande.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RedeemPointsSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        from apps.commandes.models import Order
        order = Order.objects.get(pk=serializer.validated_data["order_id"])

        try:
            discount = LoyaltyService.redeem_points(
                user=request.user,
                order=order,
                points_to_spend=serializer.validated_data["points_to_spend"],
            )
            return Response({
                "success": True,
                "points_spent": serializer.validated_data["points_to_spend"],
                "discount_amount": str(discount),
                "order_total_after": str(order.total_final),
            })
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LoyaltyEventsView(ListAPIView):
    """
    GET /api/v1/loyalty/events/
    Journal paginé des événements de points de l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LoyaltyEventSerializer

    def get_queryset(self):
        return LoyaltyEvent.objects.filter(
            user=self.request.user
        ).order_by("-created_at")


class ReferralView(APIView):
    """
    GET /api/v1/loyalty/referral/
    Code de parrainage + statistiques des filleuls.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = LoyaltyProfile.objects.get(user=request.user)
        except LoyaltyProfile.DoesNotExist:
            return Response(
                {"detail": "Profil introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        referrals = profile.referrals.select_related("user").all()
        referral_data = []
        for ref in referrals:
            first_purchase = LoyaltyEvent.objects.filter(
                user=ref.user, reason=LoyaltyEvent.Reason.FIRST_PURCHASE
            ).exists()
            referral_data.append({
                "email": ref.user.email,
                "joined_at": ref.created_at,
                "has_purchased": first_purchase,
            })

        return Response({
            "referral_code": profile.referral_code,
            "referral_count": referrals.count(),
            "referrals": referral_data,
        })


# ─── Admin ────────────────────────────────────────────────────────────────

class AdminLoyaltyProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD admin pour les profils de fidélité.
    GET    /api/v1/loyalty/admin/profiles/
    PATCH  /api/v1/loyalty/admin/profiles/{id}/
    """
    queryset = LoyaltyProfile.objects.select_related("user", "tier").all()
    serializer_class = LoyaltyProfileSerializer
    permission_classes = [IsPlatformAdmin]
    search_fields = ("user__email", "referral_code")

    @action(detail=False, methods=["post"])
    def adjust_points(self, request):
        """
        POST /api/v1/loyalty/admin/adjust-points/
        Ajustement manuel de points par un administrateur.
        """
        serializer = AdminAdjustPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        points = serializer.validated_data["points"]
        reason_text = serializer.validated_data["reason"]

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Utilisateur introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from django.db import transaction
        with transaction.atomic():
            profile = LoyaltyProfile.objects.select_for_update().get(user=user)
            profile.points_balance = models.F("points_balance") + points
            if points > 0:
                profile.total_points_earned = models.F("total_points_earned") + points
            profile.save(update_fields=["points_balance", "total_points_earned", "updated_at"])
            profile.refresh_from_db()

            LoyaltyEvent.objects.create(
                user=user,
                points_delta=points,
                new_points_balance_after=profile.points_balance,
                reason=LoyaltyEvent.Reason.ADMIN_ADJUSTMENT,
                description=reason_text,
            )

        return Response({
            "success": True,
            "user_email": user.email,
            "points_adjusted": points,
            "new_balance": profile.points_balance,
        })