from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0015_client_service_period"),
    ]

    operations = [
        migrations.AlterField(
            model_name="clientserviceperiod",
            name="status",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "Activo"),
                    ("QUEUED", "Por iniciar"),
                    ("EXPIRED", "Vencido"),
                    ("CANCELLED", "Cancelado"),
                ],
                default="ACTIVE",
                max_length=16,
                verbose_name="Estado",
            ),
        ),
    ]
