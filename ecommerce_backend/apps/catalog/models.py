from apps.core.models import BaseModel
from django.db import models






class Category(BaseModel):
    name = models.CharField(max_length=100)

    slug = models.SlugField(
        unique=True,
        db_index=True,
        null=True,
        blank=True
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    description = models.TextField(blank=True)

    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name





class Product(BaseModel):

    class ProductType(models.TextChoices):
        RAW = "RAW", "Brut"
        PROCESSED = "PROCESSED", "Transformé"
        EXPORT = "EXPORT", "Export"

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )

    name = models.CharField(max_length=255)

    slug = models.SlugField(
        unique=True,
        db_index=True,
        null=True,
        blank=True
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    description = models.TextField(
        null=True,
        blank=True
    )

    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    stock = models.PositiveIntegerField(
        default=0,
    )

    weight_grams = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    seo_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    seo_description = models.TextField(
        blank=True,
        null=True,
    )

    is_top = models.BooleanField(
        default=False,
        null=True,
        blank=True,
    )

    related_products = models.ManyToManyField(
        "self",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["price"]),
            models.Index(fields=["is_active"]),
        ]

    @property
    def is_in_stock(self):
        return self.stock > 0


    @property
    def effective_price(self):

        first_variant = self.variants.first()

        if first_variant:
            return first_variant.price

        return self.price


    
    @property
    def effective_stock(self):

        first_variant = self.variants.first()

        if first_variant:
            return sum(
                variant.stock
                for variant in self.variants.all()
            )

        return self.stock


    

    # @property
    # def discount_percentage(self):
    #     if self.compare_price and self.compare_price > self.price:
    #         return round(
    #             (
    #                 (self.compare_price - self.price)
    #                 / self.compare_price
    #             ) * 100
    #         )
    #     return 0

    def __str__(self):
        return self.name








class ProductImage(BaseModel):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="products/%Y/%m/",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-is_primary"]

    def __str__(self):
        return self.product.name






class ProductVariant(BaseModel):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    name = models.CharField(
        max_length=100,
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        null=True,
        blank=True
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    stock = models.PositiveIntegerField(
        default=0,
    )

    weight_grams = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.product.name} - {self.name}"





