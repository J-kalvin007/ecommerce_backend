from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from rest_framework import status
from rest_framework.generics import ListAPIView, DestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Favorite
from .serializers import ToggleFavoriteSerializer, FavoriteProductSerializer
from django.http import Http404



from rest_framework.permissions import AllowAny, IsAuthenticated


from .models import Product
from .models import Rating
from .serializers import RateSerializer, RatingDetailSerializer






from rest_framework.filters import (
    OrderingFilter,
    SearchFilter,
)

from rest_framework.permissions import (
    AllowAny,
)

from rest_framework.viewsets import (
    ModelViewSet,
    ReadOnlyModelViewSet,
)

from apps.core.permissions import (
    IsPlatformAdmin,
)

from .filters import ProductFilter

from .models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
)

from .serializers import (
    CategorySerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductImageAdminSerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ProductVariantAdminSerializer,
    ProductVariantSerializer,
)


# =====================================================
# PUBLIC CATEGORY
# =====================================================

class CategoryViewSet(ReadOnlyModelViewSet):

    permission_classes = [AllowAny]

    serializer_class = CategorySerializer

    queryset = (
        Category.objects
        .filter(is_active=True)
        .prefetch_related("children")
    )


# =====================================================
# PUBLIC PRODUCT
# =====================================================

class ProductViewSet(ReadOnlyModelViewSet):

    permission_classes = [AllowAny]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "description",
        "category__name",
        "sku",
    ]

    ordering_fields = [
        "price",
        "created_at",
        "name",
    ]

    queryset = (
        Product.objects
        .filter(is_active=True)
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
            "related_products",
        )
    )

    def get_serializer_class(self):

        if self.action == "retrieve":
            return ProductDetailSerializer

        return ProductListSerializer


# =====================================================
# ADMIN CATEGORY
# =====================================================

class CategoryAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    serializer_class = CategorySerializer

    queryset = (
        Category.objects
        .all()
        .prefetch_related("children")
    )


# =====================================================
# ADMIN PRODUCT
# =====================================================

class ProductAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    queryset = (
        Product.objects
        .all()
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
            "related_products",
        )
    )

    def get_serializer_class(self):

        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            return ProductCreateUpdateSerializer

        return ProductDetailSerializer


# =====================================================
# ADMIN PRODUCT IMAGE
# =====================================================

class ProductImageAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    serializer_class = ProductImageAdminSerializer

    queryset = (
        ProductImage.objects
        .select_related("product")
    )


# =====================================================
# ADMIN PRODUCT VARIANT
# =====================================================

class ProductVariantAdminViewSet(ModelViewSet):

    permission_classes = [
        IsPlatformAdmin
    ]

    serializer_class = ProductVariantAdminSerializer

    queryset = (
        ProductVariant.objects
        .select_related("product")
    )







"""
Vues DRF pour le module de favoris.

Deux endpoints :
- POST /toggle/ : toggle atomique (ajout/suppression)
- GET /my-favorites/ : liste paginée des favoris de l'utilisateur connecté
- DELETE /<product_id>/ : suppression explicite d'un favori
"""




class ToggleFavoriteView(APIView):
    """
    POST /api/v1/favorites/toggle/
    
    Endpoint unique pour ajouter ou retirer un produit des favoris.
    Utilise get_or_create dans une transaction atomique pour garantir
    l'idempotence et éviter les race conditions.
    
    Permission: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ToggleFavoriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]

        # get_or_create est atomique grâce à la contrainte unique_together
        # en base de données. Si deux requêtes concurrentes arrivent,
        # une seule créera l'enregistrement, l'autre lèvera une IntegrityError
        # que get_or_create gère en retentant un get.
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            product_id=product_id,
        )

        if created:
            # Le produit vient d'être ajouté aux favoris
            return Response(
                {
                    "favorited": True,
                    "count_favorites": favorite.product.count_favorites,
                    "product_id": str(product_id),
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            # Le produit était déjà en favori → on le retire
            favorite.delete()
            # Recharger le produit pour avoir le compteur à jour
            from apps.catalog.models import Product
            product = Product.objects.get(pk=product_id)
            return Response(
                {
                    "favorited": False,
                    "count_favorites": product.count_favorites,
                    "product_id": str(product_id),
                },
                status=status.HTTP_200_OK,
            )






class MyFavoritesView(ListAPIView):
    """
    GET /api/v1/favorites/my-favorites/
    
    Retourne la liste paginée des produits favoris de l'utilisateur connecté.
    Les produits sont ordonnés du plus récemment ajouté au plus ancien.
    
    Permission: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteProductSerializer

    def get_queryset(self):
        """
        Retourne les favoris de l'utilisateur avec prefetch du produit
        et de ses images pour optimiser les requêtes SQL.
        """
        return (
            Favorite.objects
            .filter(user=self.request.user)
            .select_related("product")
            .prefetch_related("product__images")
            .order_by("-created_at")
        )




class DeleteFavoriteView(DestroyAPIView):
    """
    DELETE /api/v1/favorites/{product_id}/
    
    Supprime un produit spécifique des favoris de l'utilisateur connecté.
    Retourne 404 si le favori n'existe pas.
    
    Permission: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Récupère le favori par product_id pour l'utilisateur courant."""
       
        try:
            return Favorite.objects.get(
                user=self.request.user,
                product_id=self.kwargs["product_id"],
            )
        except Favorite.DoesNotExist:
            raise Http404("Ce produit n'est pas dans vos favoris.")

    def perform_destroy(self, instance):
        """Supprime le favori (le signal post_delete mettra à jour le compteur)."""
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        """
        Supprime le favori et retourne une réponse confirmant l'action.
        """
        instance = self.get_object()
        product_id = instance.product_id
        self.perform_destroy(instance)

        
        product = Product.objects.get(pk=product_id)
        return Response(
            {
                "favorited": False,
                "count_favorites": product.count_favorites,
                "product_id": str(product_id),
            },
            status=status.HTTP_200_OK,
        )
    






    """
Vues DRF pour le module de notation.

Endpoints :
- POST /rate/ : créer ou modifier une note (upsert)
- GET /{product_id}/ : détails de notation d'un produit
- DELETE /{product_id}/ : supprimer sa note
"""

class RateProductView(APIView):
    """
    POST /api/v1/ratings/rate/
    
    Crée ou modifie la note d'un utilisateur sur un produit.
    Utilise update_or_create pour l'upsert atomique.
    
    Permission: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = RateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        score = serializer.validated_data["score"]

        product = Product.objects.get(pk=product_id)

        # update_or_create est atomique grâce à la contrainte unique_together
        # Si l'utilisateur a déjà noté, on met à jour le score.
        # Sinon, on crée une nouvelle note.
        rating, created = Rating.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={"score": score},
        )

        # Recharger le produit pour avoir les agrégats à jour
        product.refresh_from_db()

        return Response(
            {
                "rated": True,
                "user_score": rating.score,
                "note_produit": str(product.note_produit),
                "count_ratings": product.count_ratings,
                "product_id": str(product_id),
                "updated": not created,  # True si c'était une modification
            },
            status=status.HTTP_200_OK,
        )


class ProductRatingDetailView(APIView):
    """
    GET /api/v1/ratings/{product_id}/
    
    Retourne les détails de notation d'un produit :
    - Distribution par étoile (1★ à 5★)
    - Note moyenne globale
    - Note de l'utilisateur connecté (si authentifié)
    
    Permission: AllowAny (page publique), mais le user_score dépend de l'auth.
    """
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Produit introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RatingDetailSerializer(
            product,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteRatingView(DestroyAPIView):
    """
    DELETE /api/v1/ratings/{product_id}/
    
    Supprime la note de l'utilisateur connecté pour un produit donné.
    Retourne 404 si aucune note n'existe.
    
    Permission: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Récupère la note par product_id pour l'utilisateur courant."""
        
        try:
            return Rating.objects.get(
                user=self.request.user,
                product_id=self.kwargs["product_id"],
            )
        except Rating.DoesNotExist:
            raise Http404("Vous n'avez pas noté ce produit.")

    def perform_destroy(self, instance):
        """Supprime la note (le signal post_delete recalculera les agrégats)."""
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        """
        Supprime la note et retourne les agrégats mis à jour.
        """
        instance = self.get_object()
        product_id = instance.product_id
        self.perform_destroy(instance)

        
        product = Product.objects.get(pk=product_id)
        return Response(
            {
                "rated": False,
                "user_score": None,
                "note_produit": str(product.note_produit),
                "count_ratings": product.count_ratings,
                "product_id": str(product_id),
            },
            status=status.HTTP_200_OK,
        )