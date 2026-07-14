from django.db import migrations


def populate_products(apps, schema_editor):
    """Create a Product for each distinct (vendor, name) already in inventory,
    carrying over the mapped flower, and point each InventoryItem at it."""
    InventoryItem = apps.get_model("catalog", "InventoryItem")
    Product = apps.get_model("catalog", "Product")
    for item in InventoryItem.objects.all():
        product, _ = Product.objects.get_or_create(
            vendor_id=item.vendor_id,
            name=item.name,
            defaults={"flower_id": item.flower_id},
        )
        if product.flower_id is None and item.flower_id is not None:
            product.flower_id = item.flower_id
            product.save(update_fields=["flower"])
        item.product = product
        item.save(update_fields=["product"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0010_alter_inventoryitem_flower_product_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_products, migrations.RunPython.noop),
    ]
