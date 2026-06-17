from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lockers", "0002_lockerrental_membership"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lockerrental",
            name="status",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "Activo"),
                    ("QUEUED", "Por iniciar"),
                    ("EXPIRED", "Vencido"),
                    ("RELEASED", "Liberado"),
                    ("CANCELLED", "Cancelado"),
                ],
                default="ACTIVE",
                max_length=16,
                verbose_name="Estado",
            ),
        ),
    ]
