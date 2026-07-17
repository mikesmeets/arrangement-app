from django.db import migrations, models


def carry_expiry_to_line_items(apps, schema_editor):
    """An expired invoice expired everything on it. Now that flowers and hard
    goods expire independently, push the invoice's state down onto its lines."""
    Invoice = apps.get_model("catalog", "Invoice")
    InvoiceLineItem = apps.get_model("catalog", "InvoiceLineItem")
    for invoice in Invoice.objects.filter(expired=True):
        InvoiceLineItem.objects.filter(invoice=invoice).update(
            expired=True, expired_on=invoice.expired_on
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0022_alter_invoicelineitem_kind_alter_product_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoicelineitem",
            name="expired",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="invoicelineitem",
            name="expired_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(carry_expiry_to_line_items, migrations.RunPython.noop),
        migrations.RemoveField(model_name="invoice", name="expired"),
        migrations.RemoveField(model_name="invoice", name="expired_on"),
    ]
