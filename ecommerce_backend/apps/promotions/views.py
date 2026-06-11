"""
Vues DRF pour le module promotions.

Endpoints :
- Publics : liste codes, flash sales, bannières
- Authentifiés : validation et application de code promo
- Admin : CRUD complet
"""
import uuid
from django.db import models
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsPlatformAdmin
from .exceptions import PromoCodeError
from .models import PromoCode, Soldes, Banner
from .serializers import (
    PromoCodeListSerializer,
    ValidateCodeSerializer,
    ApplyCodeSerializer,
    SoldesSerializer,
    BannerSerializer,
    AdminPromoCodeSerializer,
    AdminSoldesSerializer,
    AdminBannerSerializer,
)
from .services import PromoService


# ─── Public ────────────────────────────────────────────────────────────────

class ActivePromoCodesView(APIView):
    """
    GET /api/v1/promotions/codes/
    Liste des codes promo actifs (public).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        now = timezone.now()
        codes = PromoCode.objects.filter(
            is_active=True,
            starts_at__lte=now,
        ).exclude(
            expires_at__isnull=False,
            expires_at__lt=now,
        ).exclude(
            max_uses__gt=0,
            number_times_used__gte=models.F("max_uses"),
        ).order_by("-created_at")[:20]

        serializer = PromoCodeListSerializer(codes, many=True)
        return Response(serializer.data)


class ValidatePromoCodeView(APIView):
    """
    POST /api/v1/promotions/codes/validate/
    Valide un code promo sans l'appliquer.
    Retourne la réduction potentielle.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidateCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            promo, discount = PromoService.validate_code(
                code=serializer.validated_data["code"],
                user=request.user,
                cart_total=serializer.validated_data["cart_total"],
            )
            return Response({
                "valid": True,
                "code": promo.code,
                "type": promo.type,
                "value": str(promo.value),
                "discount_amount": str(discount),
                "description": promo.description,
            })
        except PromoCodeError as e:
            return Response({
                "valid": False,
                "error_code": e.code,
                "detail": e.message,
            }, status=status.HTTP_400_BAD_REQUEST)


class ApplyPromoCodeView(APIView):
    """
    POST /api/v1/promotions/codes/apply/
    Applique un code promo à une commande.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ApplyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.commandes.models import Order
        try:
            order = Order.objects.get(
                pk=serializer.validated_data["order_id"],
                user=request.user,
            )
        except Order.DoesNotExist:
            return Response(
                {"detail": "Commande introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Valider
            promo, discount = PromoService.validate_code(
                code=serializer.validated_data["code"],
                user=request.user,
                cart_total=order.total_final,  # Avant réduction
            )
            # Appliquer
            discount_applied = PromoService.apply_code(
                promo_code=promo,
                user=request.user,
                order=order,
                discount_amount=discount,
            )
            return Response({
                "applied": True,
                "code": promo.code,
                "discount_amount": str(discount_applied),
                "order_total_after": str(order.total_final),
            })
        except PromoCodeError as e:
            return Response({
                "applied": False,
                "error_code": e.code,
                "detail": e.message,
            }, status=status.HTTP_400_BAD_REQUEST)


class ActiveFlashSalesView(APIView):
    """
    GET /api/v1/promotions/flash-sales/
    Flash sales en cours (public).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        flash_sales = PromoService.get_active_flash_sales()
        serializer = SoldesSerializer(
            flash_sales, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ActiveBannersView(APIView):
    """
    GET /api/v1/promotions/banners/
    Bannières actives (public). Filtre optionnel ?type=CAROUSEL
    """
    permission_classes = [AllowAny]

    def get(self, request):
        banner_type = request.query_params.get("type")
        banners = PromoService.get_active_banners(banner_type=banner_type)
        serializer = BannerSerializer(
            banners, many=True, context={"request": request}
        )
        return Response(serializer.data)


# ─── Admin ────────────────────────────────────────────────────────────────

class AdminPromoCodeViewSet(viewsets.ModelViewSet):
    """
    CRUD admin pour les codes promo.
    POST   /api/v1/promotions/admin/codes/
    GET    /api/v1/promotions/admin/codes/{id}/
    """
    queryset = PromoCode.objects.all().order_by("-created_at")
    serializer_class = AdminPromoCodeSerializer
    permission_classes = [IsPlatformAdmin]

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplique un code promo existant."""
        original = self.get_object()
        original.pk = None
        original.code = f"{original.code}-COPY-{uuid.uuid4().hex[:4].upper()}"
        original.number_times_used = 0
        original.save()
        serializer = self.get_serializer(original)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def deactivate_expired(self, request):
        """Désactive en masse tous les codes expirés."""
        from django.utils import timezone
        count = PromoCode.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now(),
        ).update(is_active=False)
        return Response({"deactivated": count})


class AdminFlashSaleViewSet(viewsets.ModelViewSet):
    """CRUD admin pour les ventes flash."""
    queryset = Soldes.objects.all().order_by("-starts_at")
    serializer_class = AdminSoldesSerializer
    permission_classes = [IsPlatformAdmin]


class AdminBannerViewSet(viewsets.ModelViewSet):
    """CRUD admin pour les bannières."""
    queryset = Banner.objects.all().order_by("banner_type", "position")
    serializer_class = AdminBannerSerializer
    permission_classes = [IsPlatformAdmin]