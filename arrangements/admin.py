from django.contrib import admin

from .models import Arrangement, ArrangementItem


class ArrangementItemInline(admin.TabularInline):
    model = ArrangementItem
    extra = 1


@admin.register(Arrangement)
class ArrangementAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "type", "shopify_collection", "status", "suggested_price", "profit"]
    list_filter = ["status", "type"]
    search_fields = ["name", "sku", "tags"]
    readonly_fields = ["sku"]
    inlines = [ArrangementItemInline]
