from django.db import migrations

REPORT_VIEW = "reports.view"
REPORT_SEND = "reports.send"
SETTINGS_REPORTS = "settings.reports"

CASHIER_REPORT_PERMS = (REPORT_VIEW, REPORT_SEND)
ADMIN_EXTRA_PERMS = (REPORT_VIEW, REPORT_SEND, SETTINGS_REPORTS)


def add_reports_permissions(apps, schema_editor):
    StaffRole = apps.get_model("users", "StaffRole")

    for role in StaffRole.objects.all():
        perms = list(role.permissions or [])
        changed = False
        if role.name == "Administrador":
            for code in ADMIN_EXTRA_PERMS:
                if code not in perms:
                    perms.append(code)
                    changed = True
        elif role.name in ("Encargado en caja", "Cajera"):
            for code in CASHIER_REPORT_PERMS:
                if code not in perms:
                    perms.append(code)
                    changed = True
        if changed:
            role.permissions = perms
            role.save(update_fields=["permissions"])


def remove_reports_permissions(apps, schema_editor):
    StaffRole = apps.get_model("users", "StaffRole")
    codes = set(ADMIN_EXTRA_PERMS)

    for role in StaffRole.objects.all():
        perms = [p for p in (role.permissions or []) if p not in codes]
        if perms != (role.permissions or []):
            role.permissions = perms
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_clients_view_phone"),
    ]

    operations = [
        migrations.RunPython(add_reports_permissions, remove_reports_permissions),
    ]
