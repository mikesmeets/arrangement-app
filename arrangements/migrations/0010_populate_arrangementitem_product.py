from django.db import migrations


def populate_products(apps, schema_editor):
    """Point existing arrangement items at a Product that maps to the same
    flower. Any item with no matching product is dropped (pre-refactor data)."""
    ArrangementItem = apps.get_model("arrangements", "ArrangementItem")
    Product = apps.get_model("catalog", "Product")
    for item in ArrangementItem.objects.all():
        product = None
        if item.flower_id:
            product = Product.objects.filter(flower_id=item.flower_id).first()
        if product:
            item.product = product
            item.save(update_fields=["product"])
        else:
            item.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arrangements", "0009_alter_arrangementitem_unique_together_and_more"),
        ("catalog", "0011_populate_products"),
    ]

    operations = [
        migrations.RunPython(populate_products, migrations.RunPython.noop),
    ]
