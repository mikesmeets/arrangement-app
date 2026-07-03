from django.db import migrations


def backfill_sku(apps, schema_editor):
    Arrangement = apps.get_model("arrangements", "Arrangement")
    seq_by_prefix = {}
    for arrangement in Arrangement.objects.filter(sku="").order_by("created_at"):
        prefix = f"TB{arrangement.created_at.strftime('%y%m%d')}"
        seq = seq_by_prefix.get(prefix, 0) + 1
        seq_by_prefix[prefix] = seq
        arrangement.sku = f"{prefix}{seq:03d}"
        arrangement.save(update_fields=["sku"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("arrangements", "0005_arrangement_sku"),
    ]

    operations = [
        migrations.RunPython(backfill_sku, noop),
    ]
