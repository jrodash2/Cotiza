from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from .models import Cliente, ProductoServicio, Cotizacion, CotizacionItem


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nombre',
            'contacto',
            'telefono',
            'email',
            'direccion',
            'nit',
            'municipio',
            'departamento',
            'notas',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class ProductoServicioForm(forms.ModelForm):
    class Meta:
        model = ProductoServicio
        fields = [
            'tipo',
            'nombre',
            'descripcion',
            'unidad',
            'precio_costo',
            'precio_venta',
            'activo',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_precio_costo(self):
        precio_costo = self.cleaned_data.get('precio_costo')
        if precio_costo is not None and precio_costo < 0:
            raise forms.ValidationError('El precio de costo no puede ser negativo.')
        return precio_costo

    def clean_precio_venta(self):
        precio_venta = self.cleaned_data.get('precio_venta')
        if precio_venta is not None and precio_venta < 0:
            raise forms.ValidationError('El precio de venta no puede ser negativo.')
        return precio_venta


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = [
            'fecha_emision',
            'cliente',
            'titulo',
            'validez_dias',
            'observaciones',
            'garantia_texto',
            'estado',
        ]
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

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


class CotizacionItemForm(forms.ModelForm):
    precio_venta_unitario = forms.DecimalField(min_value=Decimal('0.00'), required=False)
    precio_costo_unitario = forms.DecimalField(min_value=Decimal('0.00'), required=False)

    class Meta:
        model = CotizacionItem
        fields = [
            'producto_servicio',
            'descripcion_editable',
            'cantidad',
            'precio_venta_unitario',
            'precio_costo_unitario',
        ]
        widgets = {
            'descripcion_editable': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        show_costs = kwargs.pop('show_costs', True)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()
        if not show_costs:
            self.fields['precio_costo_unitario'].widget = forms.HiddenInput()
            if self.instance and self.instance.pk:
                self.fields['precio_costo_unitario'].initial = self.instance.precio_costo_unitario

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor a 0.')
        return cantidad

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto_servicio')
        precio_venta = cleaned_data.get('precio_venta_unitario')
        precio_costo = cleaned_data.get('precio_costo_unitario')
        descripcion = cleaned_data.get('descripcion_editable')
        if producto:
            if precio_venta in (None, ''):
                cleaned_data['precio_venta_unitario'] = producto.precio_venta
            if precio_costo in (None, ''):
                cleaned_data['precio_costo_unitario'] = producto.precio_costo
            if not descripcion:
                cleaned_data['descripcion_editable'] = producto.descripcion
        return cleaned_data


CotizacionItemFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionItem,
    form=CotizacionItemForm,
    extra=3,
    can_delete=True,
)
