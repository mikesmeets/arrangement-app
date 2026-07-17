from django.db import migrations


def published_to_active(apps, schema_editor):
    """The old two-value status (draft/published) becomes the Shopify status
    (active/draft/unlisted). A previously-published arrangement is Active."""
    Arrangement = apps.get_model("arrangements", "Arrangement")
    Arrangement.objects.filter(status="published").update(status="active")


class Migration(migrations.Migration):

    dependencies = [
        ("arrangements", "0014_alter_arrangement_status"),
    ]

    operations = [
        migrations.RunPython(published_to_active, migrations.RunPython.noop),
    ]
