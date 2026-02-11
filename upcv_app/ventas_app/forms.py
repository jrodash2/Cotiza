from django import forms

from cotizaciones_app.models import Cliente

from .models import Venta


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['cliente']

    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.order_by('nombre'),
        required=False,
        empty_label='Consumidor final',
    )
