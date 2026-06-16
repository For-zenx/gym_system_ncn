from django.db import migrations

OPEN_TURNSTILE = "access.open_turnstile"


def add_open_turnstile_permission(apps, schema_editor):
    StaffRole = apps.get_model("users", "StaffRole")
    StaffProfile = apps.get_model("users", "StaffProfile")

    for role in StaffRole.objects.all():
        if role.name not in {"Administrador", "Encargado en caja"}:
            continue
        perms = list(role.permissions or [])
        if OPEN_TURNSTILE not in perms:
            perms.append(OPEN_TURNSTILE)
            role.permissions = perms
            role.save(update_fields=["permissions"])

    for profile in StaffProfile.objects.select_related("user").all():
        user = profile.user
        if not user:
            continue
        perms = list(profile.permissions or [])
        if OPEN_TURNSTILE in perms:
            continue
        if "roles.manage" in perms and "users.view" in perms:
            perms.append(OPEN_TURNSTILE)
            profile.permissions = perms
            profile.save(update_fields=["permissions"])


def remove_open_turnstile_permission(apps, schema_editor):
    StaffRole = apps.get_model("users", "StaffRole")
    StaffProfile = apps.get_model("users", "StaffProfile")

    for role in StaffRole.objects.all():
        perms = [p for p in (role.permissions or []) if p != OPEN_TURNSTILE]
        if perms != (role.permissions or []):
            role.permissions = perms
            role.save(update_fields=["permissions"])

    for profile in StaffProfile.objects.all():
        perms = [p for p in (profile.permissions or []) if p != OPEN_TURNSTILE]
        if perms != (profile.permissions or []):
            profile.permissions = perms
            profile.save(update_fields=["permissions"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_edit_invoice_staff_profiles"),
    ]

    operations = [
        migrations.RunPython(
            add_open_turnstile_permission,
            remove_open_turnstile_permission,
        ),
    ]
