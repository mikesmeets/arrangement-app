from collections import defaultdict
from decimal import Decimal

from django.db import migrations


def derive_inventory(apps, schema_editor):
    """Inventory becomes derived from invoice line items, so:

    1. Point every existing line item at its vendor's Product.
    2. Turn inventory that never came from an invoice (seeded / hand-added)
       into opening-stock invoices, one per vendor + received date, so that
       stock survives the InventoryItem table going away.
    3. Carry expiry from invoice-sourced inventory onto the invoice itself.
    """
    InventoryItem = apps.get_model("catalog", "InventoryItem")
    Invoice = apps.get_model("catalog", "Invoice")
    InvoiceLineItem = apps.get_model("catalog", "InvoiceLineItem")
    Product = apps.get_model("catalog", "Product")

    # 1. Link existing line items to products.
    for line_item in InvoiceLineItem.objects.select_related("invoice"):
        vendor_id = line_item.invoice.vendor_id
        if not vendor_id:
            continue
        product, _ = Product.objects.get_or_create(
            vendor_id=vendor_id,
            name=line_item.name,
            defaults={"flower_id": line_item.flower_id},
        )
        if product.flower_id is None and line_item.flower_id is not None:
            product.flower_id = line_item.flower_id
            product.save(update_fields=["flower"])
        line_item.product = product
        line_item.save(update_fields=["product"])

    # 2. Invoice-less stock -> opening-stock invoices.
    groups = defaultdict(list)
    for item in InventoryItem.objects.filter(invoice__isnull=True):
        groups[(item.vendor_id, item.date_received)].append(item)

    for (vendor_id, date_received), items in groups.items():
        invoice = Invoice.objects.create(
            vendor_id=vendor_id,
            date=date_received,
            status="confirmed",
            expired=all(i.expired for i in items),
            expired_on=next((i.expired_on for i in items if i.expired_on), None),
        )
        for item in items:
            quantity = item.quantity or 0
            per_stem = item.per_stem_cost or Decimal("0.00")
            InvoiceLineItem.objects.create(
                invoice=invoice,
                product_id=item.product_id,
                name=item.name,
                quantity=quantity,
                total_cost=(per_stem * quantity).quantize(Decimal("0.01")),
                per_stem_cost=per_stem,
                flower_id=item.flower_id,
                size=item.size,
                grade=item.grade,
            )

    # 3. An invoice whose stock was entirely expired is now an expired invoice.
    by_invoice = defaultdict(list)
    for item in InventoryItem.objects.filter(invoice__isnull=False):
        by_invoice[item.invoice_id].append(item)
    for invoice_id, items in by_invoice.items():
        if items and all(i.expired for i in items):
            Invoice.objects.filter(pk=invoice_id).update(
                expired=True,
                expired_on=next((i.expired_on for i in items if i.expired_on), None),
            )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0018_invoice_expired_invoicelineitem_product"),
    ]

    operations = [
        migrations.RunPython(derive_inventory, migrations.RunPython.noop),
    ]
