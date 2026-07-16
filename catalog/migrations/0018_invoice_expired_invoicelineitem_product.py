import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0017_customer_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="expired",
            field=models.BooleanField(
                default=False,
                help_text="Perished delivery — its flowers stop counting as stock.",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="expired_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="invoicelineitem",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="line_items",
                to="catalog.product",
            ),
        ),
    ]
