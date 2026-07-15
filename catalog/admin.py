from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Customer,
    Flower,
    FlowerCategory,
    FlowerVariety,
    GlobalSettings,
    InventoryItem,
    Invoice,
    InvoiceLineItem,
    Product,
    Subscription,
    Vendor,
)


@admin.register(FlowerCategory)
class FlowerCategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(FlowerVariety)
class FlowerVarietyAdmin(admin.ModelAdmin):
    list_display = ["name", "category"]
    list_filter = ["category"]
    search_fields = ["name"]


@admin.register(Flower)
class FlowerAdmin(admin.ModelAdmin):
    list_display = ["thumbnail", "__str__", "category", "variety", "design_category", "quantity_on_hand", "current_avg_cost"]
    list_filter = ["category", "design_category", "type"]
    search_fields = ["variety__name", "color"]

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:32px;height:32px;border-radius:50%;">', obj.image.url)
        return ""
    thumbnail.short_description = ""


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["name", "abbreviation", "contact_name", "phone", "email", "website"]
    search_fields = ["name", "abbreviation", "contact_name"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["customer", "sub_name"]
    list_filter = ["customer"]
    search_fields = ["customer__name", "sub_name"]


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1
    readonly_fields = ["per_stem_cost"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["vendor", "vendor_invoice_number", "date", "status"]
    list_filter = ["status", "vendor"]
    search_fields = ["vendor_invoice_number"]
    inlines = [InvoiceLineItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "vendor", "flower", "quantity_on_hand", "current_avg_cost"]
    list_filter = ["vendor"]
    search_fields = ["name"]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ["name", "product", "vendor", "quantity", "per_stem_cost", "date_received", "expired"]
    list_filter = ["expired", "vendor", "flower__category"]
    search_fields = ["name"]


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ["markup_multiplier"]

    def has_add_permission(self, request):
        return not GlobalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
