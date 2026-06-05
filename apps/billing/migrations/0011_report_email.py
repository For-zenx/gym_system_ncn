import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0010_saleitem_invoiceline"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportEmailSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "recipient_email",
                    models.EmailField(
                        blank=True,
                        default="",
                        max_length=254,
                        verbose_name="Correo del dueño (reportes)",
                    ),
                ),
                (
                    "daily_send_limit",
                    models.PositiveSmallIntegerField(
                        default=3,
                        verbose_name="Límite de envíos por día",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Actualizado"),
                ),
            ],
            options={
                "verbose_name": "Configuración de reportes por correo",
                "verbose_name_plural": "Configuración de reportes por correo",
            },
        ),
        migrations.CreateModel(
            name="ReportSendLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("sent_at", models.DateTimeField(auto_now_add=True, verbose_name="Enviado")),
                ("period_days", models.PositiveSmallIntegerField(verbose_name="Días del período")),
                ("recipient_email", models.EmailField(max_length=254, verbose_name="Destinatario")),
                ("success", models.BooleanField(default=False, verbose_name="Éxito")),
                ("error_message", models.TextField(blank=True, verbose_name="Error")),
                (
                    "sent_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="report_send_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Envío de reporte",
                "verbose_name_plural": "Envíos de reportes",
                "ordering": ["-sent_at"],
            },
        ),
    ]
