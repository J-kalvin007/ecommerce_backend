

from django.db import models
from apps.core.models import BaseModel
from apps.catalog.models import Product
from django.conf import settings
import uuid
from django.utils import timezone






class Cart(BaseModel):

    user = models.OneToOneField(
        
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    class Meta:
        db_table = "commandes_carts"
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"

    def __str__(self):
        return f"Panier - {self.user.email}"
    





class CartItem(BaseModel):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "commandes_cart_items"
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity









class OrderStatus(models.TextChoices):

    DRAFT = "draft", "Brouillon"

    PENDING_PAYMENT = (
        "pending_payment",
        "Paiement en attente",
    )

    PAID = "paid", "Payée"

    CONFIRMED = "confirmed", "Confirmée"

    PROCESSING = "processing", "Préparation"

    SHIPPED = "shipped", "Expédiée"

    DELIVERED = "delivered", "Livrée"

    CANCELLED = "cancelled", "Annulée"

    REFUNDED = "refunded", "Remboursée"








class Order(BaseModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    reference = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING_PAYMENT,
        db_index=True,
    )

    address_livraison = models.CharField(max_length=200)

 

    items_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    frais_livraison = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    notes = models.TextField(blank=True)

    phone_livraison = models.CharField(
        max_length=30,
        blank=True,
    )

    country = models.CharField(max_length=100)

    city = models.CharField(max_length=100)


    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "commandes_orders"
        ordering = ["-created_at"]
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"

    def __str__(self):
        return self.reference
    
    def save(self, *args, **kwargs):

        if not self.reference:

            date_part = timezone.now().strftime("%Y%m%d")

            unique_part = uuid.uuid4().hex[:4].upper()

            self.reference = (
                f"CMD-{date_part}-{unique_part}"
            )

        super().save(*args, **kwargs)








class OrderItem(BaseModel):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )

    product_name = models.CharField(
        max_length=255,
    )

    product_sku = models.CharField(
        max_length=100,
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    class Meta:
        db_table = "commandes_order_items"
        verbose_name = "Article commandé"
        verbose_name_plural = "Articles commandés"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"








class OrderStatusHistory(BaseModel):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    old_status = models.CharField(
        max_length=30,
        blank=True,
    )

    new_status = models.CharField(
        max_length=30,
    )

    comment = models.TextField(blank=True)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )