from django import forms
from django.forms import BaseFormSet, formset_factory

from cotizaciones_app.models import Cliente

from .models import Venta


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['cliente', 'estado', 'titulo', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.order_by('nombre'),
        required=False,
        empty_label='Consumidor final',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()


class VentaItemForm(forms.Form):
    TIPO_ARTICULO = 'articulo'
    TIPO_SERVICIO = 'servicio'
    TIPO_CHOICES = [
        (TIPO_ARTICULO, 'Artículo'),
        (TIPO_SERVICIO, 'Servicio'),
    ]

    item_type = forms.ChoiceField(choices=TIPO_CHOICES, widget=forms.HiddenInput())
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    item_label = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cantidad = forms.DecimalField(min_value=0.01, decimal_places=2, widget=forms.NumberInput(attrs={'step': '0.01'}))
    precio_unitario = forms.DecimalField(min_value=0, decimal_places=2, widget=forms.NumberInput(attrs={'step': '0.01'}))
    stock = forms.DecimalField(required=False, decimal_places=2, widget=forms.HiddenInput())
    DELETE = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_label'].widget.attrs['readonly'] = True
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()


class BaseVentaItemFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        valid_items = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            if form.cleaned_data.get('item_type') and form.cleaned_data.get('item_id'):
                valid_items += 1
        if valid_items == 0:
            raise forms.ValidationError('Debes agregar al menos un ítem a la venta.')


VentaItemFormSet = formset_factory(
    VentaItemForm,
    formset=BaseVentaItemFormSet,
    extra=0,
    can_delete=True,
)
