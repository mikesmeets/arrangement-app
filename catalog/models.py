from decimal import Decimal

from django.db import models
from django.utils import timezone


class FlowerCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "flower categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class FlowerVariety(models.Model):
    category = models.ForeignKey(
        FlowerCategory, on_delete=models.CASCADE, related_name="varieties"
    )
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "flower varieties"
        ordering = ["category__name", "name"]
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Flower(models.Model):
    TYPE_STEM = "stem"
    TYPE_BRANCH = "branch"
    TYPE_PLANT = "plant"
    TYPE_BUNCH = "bunch"
    TYPE_CHOICES = [
        (TYPE_STEM, "Stem"),
        (TYPE_BRANCH, "Branch"),
        (TYPE_PLANT, "Plant"),
        (TYPE_BUNCH, "Bunch"),
    ]

    DESIGN_FOCAL = "focal"
    DESIGN_FILLER = "filler"
    DESIGN_LINE = "line"
    DESIGN_GREENERY = "greenery"
    DESIGN_CATEGORY_CHOICES = [
        (DESIGN_FOCAL, "Focal"),
        (DESIGN_FILLER, "Filler"),
        (DESIGN_LINE, "Line"),
        (DESIGN_GREENERY, "Greenery"),
    ]

    category = models.ForeignKey(
        FlowerCategory, on_delete=models.PROTECT, related_name="flowers"
    )
    variety = models.ForeignKey(
        FlowerVariety, on_delete=models.PROTECT, related_name="flowers"
    )
    color = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    design_category = models.CharField(
        max_length=10, choices=DESIGN_CATEGORY_CHOICES
    )
    image = models.ImageField(upload_to="flowers/%Y/%m/", blank=True, null=True)

    class Meta:
        verbose_name_plural = "flowers"
        ordering = ["category__name", "variety__name", "color"]
        unique_together = ("category", "variety", "color", "type", "design_category")

    def __str__(self):
        return f"{self.variety.name} - {self.color} ({self.get_type_display()})"

    @property
    def current_avg_cost(self):
        result = InvoiceLineItem.objects.filter(
            product__flower=self, invoice__expired=False
        ).aggregate(avg=models.Avg("per_stem_cost"))
        avg = result["avg"]
        return avg.quantize(Decimal("0.01")) if avg is not None else Decimal("0.00")

    @property
    def quantity_on_hand(self):
        return sum((p.quantity_on_hand for p in self.products.all()), Decimal("0"))

    @property
    def swatch_background(self):
        from .thumbnails import colors_for

        colors = colors_for(self.color)
        if len(colors) == 1:
            return colors[0]
        return f"linear-gradient(90deg, {colors[0]} 50%, {colors[1]} 50%)"


class Vendor(models.Model):
    name = models.CharField(max_length=150, unique=True)
    abbreviation = models.CharField(
        max_length=12, blank=True, default="", help_text="Short code shown before product names, e.g. MAY"
    )
    contact_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True, default="")
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="subscriptions"
    )
    sub_name = models.CharField(
        max_length=150, blank=True, default="", help_text="Business or personal name for this subscription"
    )
    current_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ["customer__name", "sub_name"]

    def __str__(self):
        return f"{self.customer} — {self.sub_name}" if self.sub_name else str(self.customer)


class Product(models.Model):
    """A vendor's named product — the base inventory/arrangement unit. Only the
    plain product name is stored; the "<abbr> - <name>" label is computed and
    used just in the arrangement maker. The Flower taxonomy link is optional, so
    the app works without it."""

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=150)
    flower = models.ForeignKey(
        Flower,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    class Meta:
        ordering = ["vendor__name", "name"]
        unique_together = ("vendor", "name")

    def __str__(self):
        return self.name

    @property
    def label(self):
        """Vendor-abbreviated label, e.g. "MAY - Freedom Rose Red 50cm".
        Computed on the fly (never stored) — shown in the inventory and
        arrangement-maker screens."""
        prefix = self.vendor.abbreviation or self.vendor.name
        return f"{prefix} - {self.name}"

    @property
    def quantity_in(self):
        """Stems received, from the line items of unexpired invoices."""
        result = self.line_items.filter(invoice__expired=False).aggregate(
            total=models.Sum("quantity")
        )
        return Decimal(result["total"] or 0)

    @property
    def quantity_used(self):
        """Stems consumed by arrangements."""
        result = self.arrangement_items.aggregate(total=models.Sum("quantity"))
        return Decimal(result["total"] or 0)

    @property
    def quantity_on_hand(self):
        """Inventory is derived, never stored: what came in less what was used."""
        return self.quantity_in - self.quantity_used

    @property
    def current_avg_cost(self):
        result = self.line_items.filter(invoice__expired=False).aggregate(
            avg=models.Avg("per_stem_cost")
        )
        avg = result["avg"]
        return avg.quantize(Decimal("0.01")) if avg is not None else Decimal("0.00")

    @property
    def value_in(self):
        """What this product cost across unexpired invoices."""
        result = self.line_items.filter(invoice__expired=False).aggregate(
            total=models.Sum("total_cost")
        )
        return result["total"] or Decimal("0.00")

    @property
    def value_used(self):
        """Dollar value of the stems arrangements consumed."""
        return (self.quantity_used * self.current_avg_cost).quantize(Decimal("0.01"))

    @property
    def usage_ratio(self):
        """Share of spend consumed — None when nothing was bought."""
        if not self.value_in:
            return None
        return self.value_used / self.value_in


class Invoice(models.Model):
    STATUS_PENDING = "pending_review"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Review"),
        (STATUS_CONFIRMED, "Confirmed"),
    ]

    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="invoices", null=True, blank=True
    )
    vendor_invoice_number = models.CharField(max_length=100, blank=True, default="")
    date = models.DateField(default=timezone.now)
    file = models.FileField(upload_to="invoices/%Y/%m/", blank=True, null=True)
    raw_extracted_data = models.JSONField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    expired = models.BooleanField(
        default=False, help_text="Perished delivery — its flowers stop counting as stock."
    )
    expired_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        vendor_name = self.vendor.name if self.vendor else "New Invoice"
        return f"{vendor_name} — {self.date}"

    @property
    def total_cost(self):
        total = Decimal("0.00")
        for item in self.line_items.all():
            total += item.total_cost
        return total

    @property
    def file_is_pdf(self):
        return bool(self.file) and self.file.name.lower().endswith(".pdf")


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="line_items",
    )
    name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField()
    total_cost = models.DecimalField(max_digits=8, decimal_places=2)
    per_stem_cost = models.DecimalField(max_digits=8, decimal_places=2, editable=False)
    flower = models.ForeignKey(
        Flower,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_line_items",
    )
    size = models.CharField(max_length=50, blank=True)
    grade = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.per_stem_cost = (
            (self.total_cost / self.quantity).quantize(Decimal("0.01"))
            if self.quantity
            else Decimal("0.00")
        )
        super().save(*args, **kwargs)


class GlobalSettings(models.Model):
    markup_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("4.00"))

    class Meta:
        verbose_name_plural = "global settings"

    def __str__(self):
        return f"Global settings (markup x{self.markup_multiplier})"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
