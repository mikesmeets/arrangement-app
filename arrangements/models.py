from decimal import Decimal

from django.db import models
from django.utils import timezone

from catalog.models import Flower, GlobalSettings, Product, Subscription


class Arrangement(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    ]

    TYPE_ARRANGEMENT = "arrangement"
    TYPE_BOUQUET = "bouquet"
    TYPE_BOUTONNIERE = "boutonniere"
    TYPE_CHOICES = [
        (TYPE_ARRANGEMENT, "Arrangement"),
        (TYPE_BOUQUET, "Bouquet"),
        (TYPE_BOUTONNIERE, "Boutonniere"),
    ]

    MODE_SUBSCRIPTION = "subscription"
    MODE_SHOPIFY = "shopify"
    MODE_RECIPE = "recipe"
    MODE_CHOICES = [
        (MODE_SUBSCRIPTION, "Subscription"),
        (MODE_SHOPIFY, "Shopify"),
        (MODE_RECIPE, "Recipe"),
    ]

    sku = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    name = models.CharField(max_length=150)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_SHOPIFY)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_ARRANGEMENT)
    description = models.TextField(blank=True)
    ai_generated_description = models.BooleanField(default=False)
    photo = models.ImageField(upload_to="arrangements/%Y/%m/", blank=True, null=True)
    price_override = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    shopify_product_id = models.CharField(max_length=50, blank=True)
    shopify_collection = models.CharField(max_length=150, blank=True)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arrangements",
        help_text="Attach to fulfil a subscription (pulls its current price).",
    )
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self._generate_sku()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_sku(cls, for_date=None):
        for_date = for_date or timezone.localdate()
        prefix = f"TB{for_date.strftime('%y%m%d')}"
        last_sku = (
            cls.objects.filter(sku__startswith=prefix)
            .order_by("-sku")
            .values_list("sku", flat=True)
            .first()
        )
        seq = 1
        if last_sku:
            try:
                seq = int(last_sku[len(prefix):]) + 1
            except ValueError:
                seq = 1
        return f"{prefix}{seq:03d}"

    @property
    def markup(self):
        return GlobalSettings.get_solo().markup_multiplier

    @property
    def flower_cost(self):
        total = Decimal("0.00")
        for item in self.items.select_related("product"):
            total += item.product.current_avg_cost * item.quantity
        return total

    @property
    def suggested_price(self):
        return (self.flower_cost * self.markup).quantize(Decimal("0.01"))

    @property
    def actual_price(self):
        if self.price_override is not None:
            return self.price_override
        return self.suggested_price

    @property
    def price_multiple(self):
        if self.flower_cost == 0:
            return None
        return (self.actual_price / self.flower_cost).quantize(Decimal("0.01"))

    @property
    def profit_at_suggested_price(self):
        return (self.suggested_price - self.flower_cost).quantize(Decimal("0.01"))

    @property
    def profit(self):
        return (self.actual_price - self.flower_cost).quantize(Decimal("0.01"))


class ArrangementItem(models.Model):
    arrangement = models.ForeignKey(
        Arrangement, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="arrangement_items"
    )
    flower = models.ForeignKey(
        Flower,
        on_delete=models.PROTECT,
        related_name="arrangement_items",
        null=True,
        blank=True,
    )
    quantity = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal("1"))

    class Meta:
        ordering = ["id"]
        unique_together = ("arrangement", "product")

    def __str__(self):
        return f"{self.product} x{self.quantity}"

    @property
    def line_cost(self):
        return self.product.current_avg_cost * self.quantity
