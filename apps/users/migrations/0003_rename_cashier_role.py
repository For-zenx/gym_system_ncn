from django.db import migrations

NEW_NAME = "Encargado en caja"
LEGACY_NAME = "Cajera"


def rename_cashier_role(apps, schema_editor):
    StaffRole = apps.get_model("users", "StaffRole")
    StaffRole.objects.filter(name=LEGACY_NAME).update(name=NEW_NAME)


def restore_cashier_role_name(apps, schema_editor):
    StaffRole = apps.get_model("users", "StaffRole")
    StaffRole.objects.filter(name=NEW_NAME, is_system=True).update(name=LEGACY_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_products_permissions"),
    ]

    operations = [
        migrations.RunPython(rename_cashier_role, restore_cashier_role_name),
    ]
