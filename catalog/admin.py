from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Flower,
    FlowerCategory,
    FlowerVariety,
    GlobalSettings,
    InventoryItem,
    Invoice,
    InvoiceLineItem,
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
    list_display = ["name", "contact_name", "phone", "email"]
    search_fields = ["name", "contact_name"]


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1
    readonly_fields = ["per_stem_cost"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["vendor", "date", "status"]
    list_filter = ["status", "vendor"]
    inlines = [InvoiceLineItemInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ["name", "flower", "vendor", "quantity", "per_stem_cost", "date_received"]
    list_filter = ["vendor", "flower__category"]
    search_fields = ["name"]


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ["markup_multiplier"]

    def has_add_permission(self, request):
        return not GlobalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
