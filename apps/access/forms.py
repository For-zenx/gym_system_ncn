from django import forms

from apps.clients.models import Client

from .models import ManualTurnstileAccess


class TurnstileControlForm(forms.Form):
    client_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput,
    )
    person_name = forms.CharField(
        required=False,
        max_length=255,
        label="Nombre de la persona",
    )
    reason = forms.ChoiceField(
        choices=ManualTurnstileAccess.Reason.choices,
        label="Razón",
    )
    custom_reason = forms.CharField(
        required=False,
        max_length=255,
        label="Explique la razón",
        widget=forms.TextInput(attrs={"placeholder": "Escriba el motivo de la apertura"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        client_id = cleaned_data.get("client_id")
        person_name = (cleaned_data.get("person_name") or "").strip()
        reason = cleaned_data.get("reason")
        custom_reason = (cleaned_data.get("custom_reason") or "").strip()
        client = None

        if client_id:
            try:
                client = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                raise forms.ValidationError("El afiliado seleccionado ya no existe.")

        if not client and not person_name:
            raise forms.ValidationError(
                "Seleccione un afiliado o indique el nombre de la persona."
            )

        if reason == ManualTurnstileAccess.Reason.OTHER and not custom_reason:
            self.add_error("custom_reason", "Indique el motivo cuando elige «Otra».")

        cleaned_data["client"] = client
        cleaned_data["person_name"] = person_name or (client.nombre if client else "")
        cleaned_data["custom_reason"] = custom_reason
        return cleaned_data
