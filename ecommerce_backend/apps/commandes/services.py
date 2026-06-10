from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models import Product
from apps.commandes.models import Order, OrderItem, OrderStatusHistory


class OrderService:

    @staticmethod
    def calculate_totals(items, products_cache):
        """
        Calcule les montants de la commande sans refaire de requêtes DB.
        """
        items_total = Decimal("0.00")

        for item in items:
            product = products_cache[str(item["product_id"])]
            quantity = item["quantity"]
            items_total += product.price * quantity

        tax_amount = Decimal("0.00")
        frais_livraison = Decimal("0.00")
        discount_amount = Decimal("0.00")
        total_final = items_total + tax_amount + frais_livraison - discount_amount

        return {
            "items_total": items_total,
            "tax_amount": tax_amount,
            "frais_livraison": frais_livraison,
            "discount_amount": discount_amount,
            "total_final": total_final,
        }

    @staticmethod
    @transaction.atomic
    def create_order(
        *,
        user,
        items,
        address_livraison,
        phone_livraison,
        city,
        country,
        notes="",
    ):
        """
        Création complète d'une commande.
        """

        if not items:
            raise ValidationError(
                "La commande doit contenir au moins un produit."
            )

        products_cache = {}

        for item in items:

            product = Product.objects.filter(
                id=item["product_id"],
                is_active=True,
            ).first()

            if not product:
                raise ValidationError(
                    "Produit introuvable."
                )

            quantity = item["quantity"]

            if quantity <= 0:
                raise ValidationError(
                    "La quantité doit être supérieure à zéro."
                )

            if product.stock < quantity:
                raise ValidationError(
                    f"Stock insuffisant pour {product.name}"
                )

            products_cache[str(product.id)] = product

        totals = OrderService.calculate_totals(items, products_cache)

        order = Order.objects.create(
            user=user,
            address_livraison=address_livraison,
            phone_livraison=phone_livraison,
            city=city,
            country=country,
            notes=notes,
            items_total=totals["items_total"],
            frais_livraison=totals["frais_livraison"],
            discount_amount=totals["discount_amount"],
            tax_amount=totals["tax_amount"],
            total_final=totals["total_final"],
        )

        order_items = []

        for item in items:

            product = products_cache[
                str(item["product_id"])
            ]

            quantity = item["quantity"]

            subtotal = (
                product.price * quantity
            )

            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=subtotal,
                )
            )

            product.stock -= quantity

            product.save(
                update_fields=["stock"]
            )

        OrderItem.objects.bulk_create(
            order_items
        )

        OrderStatusHistory.objects.create(
            order=order,
            old_status="",
            new_status=order.status,
            comment="Commande créée.",
            changed_by=user,
        )

        return order

    @staticmethod
    @transaction.atomic
    def update_status(
        *,
        order,
        new_status,
        changed_by,
        comment="",
    ):
        """
        Changement de statut.
        """

        old_status = order.status

        order.status = new_status

        order.save(
            update_fields=["status"]
        )

        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            comment=comment,
            changed_by=changed_by,
        )

        return order