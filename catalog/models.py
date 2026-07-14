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
        result = self.inventory_items.aggregate(avg=models.Avg("per_stem_cost"))
        return result["avg"] or Decimal("0.00")

    @property
    def quantity_on_hand(self):
        result = self.inventory_items.aggregate(total=models.Sum("quantity"))
        return result["total"] or 0

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


class InventoryItem(models.Model):
    flower = models.ForeignKey(
        Flower, on_delete=models.PROTECT, related_name="inventory_items"
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name="inventory_items"
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_items",
    )
    name = models.CharField(max_length=150)
    size = models.CharField(max_length=50, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    per_stem_cost = models.DecimalField(max_digits=8, decimal_places=2)
    date_received = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["-date_received"]

    def __str__(self):
        return f"{self.name} ({self.quantity} @ ${self.per_stem_cost})"


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
