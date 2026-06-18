from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0006_task035_fixed_flexible_billing"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="terms_accepted_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Términos aceptados el",
            ),
        ),
    ]
