from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from .models import (
    Cliente,
    Cotizacion,
    CotizacionItem,
    PagoVenta,
    ProductoServicio,
)


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
        widgets = {
            'notas': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

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
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

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
            raise forms.ValidationError('El precio no puede ser negativo.')
        return precio_venta


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = [
            'fecha_emision',
            'cliente',
            'titulo',
            'validez_dias',
            'descuento_porcentaje',
            'descuento_monto',
            'iva_activo',
            'iva_porcentaje',
            'observaciones',
            'garantia_texto',
            'estado',
        ]
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'descuento_porcentaje': forms.NumberInput(attrs={'min': '0', 'max': '100', 'step': '0.01'}),
            'descuento_monto': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'iva_porcentaje': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'garantia_texto': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and 'fecha_emision' in self.fields:
            self.fields['fecha_emision'].initial = timezone.now().date()
            self.fields['fecha_emision'].required = False

        if 'descuento_porcentaje' in self.fields:
            self.fields['descuento_porcentaje'].help_text = 'Ingresa porcentaje entre 0 y 100.'
            self.fields['descuento_porcentaje'].widget.attrs.update(
                {'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}
            )
        if 'descuento_monto' in self.fields:
            self.fields['descuento_monto'].help_text = 'Ingresa monto fijo de descuento en Q.'
        if 'iva_activo' in self.fields:
            self.fields['iva_activo'].help_text = 'Activa para aplicar IVA al total.'
        if 'iva_incluido' in self.fields:
            self.fields['iva_incluido'].widget.attrs.update({'class': 'form-control'})
        if 'iva_porcentaje' in self.fields:
            self.fields['iva_porcentaje'].help_text = 'Porcentaje de IVA editable.'
            self.fields['iva_porcentaje'].widget.attrs.update(
                {'class': 'form-control', 'min': '0', 'step': '0.01'}
            )

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()

    def clean(self):
        cleaned_data = super().clean()
        descuento_porcentaje = cleaned_data.get('descuento_porcentaje')
        descuento_monto = cleaned_data.get('descuento_monto')

        if descuento_porcentaje is not None and (descuento_porcentaje < 0 or descuento_porcentaje > 100):
            self.add_error('descuento_porcentaje', 'El descuento porcentual debe estar entre 0 y 100.')

        if descuento_monto is not None and descuento_monto < 0:
            self.add_error('descuento_monto', 'El descuento en monto no puede ser negativo.')

        if (descuento_porcentaje or 0) > 0 and (descuento_monto or 0) > 0:
            self.add_error('descuento_monto', 'Usa descuento en porcentaje o en monto, no ambos a la vez.')

        iva_porcentaje = cleaned_data.get('iva_porcentaje')
        if iva_porcentaje is not None and iva_porcentaje < 0:
            self.add_error('iva_porcentaje', 'El porcentaje de IVA no puede ser negativo.')

        return cleaned_data


class CotizacionItemForm(forms.ModelForm):
    class Meta:
        model = CotizacionItem
        fields = [
            'producto_servicio',
            'cantidad',
        ]

    def __init__(self, *args, **kwargs):
        kwargs.pop('show_costs', True)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor a 0.')
        return cantidad

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.producto_servicio_id:
            instance.precio_venta_unitario = instance.producto_servicio.precio_venta
            instance.precio_costo_unitario = instance.producto_servicio.precio_costo
            if not instance.descripcion_editable:
                instance.descripcion_editable = instance.producto_servicio.descripcion
        if commit:
            instance.save()
        return instance


class CotizacionItemInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        items_validos = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            producto = form.cleaned_data.get('producto_servicio')
            cantidad = form.cleaned_data.get('cantidad')
            if producto and cantidad:
                items_validos += 1
        if items_validos == 0:
            raise forms.ValidationError('Debes agregar al menos un ítem a la cotización.')


CotizacionItemFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionItem,
    form=CotizacionItemForm,
    formset=CotizacionItemInlineFormSet,
    fields=('producto_servicio', 'cantidad'),
    extra=0,
    can_delete=True,
)


class PagoVentaForm(forms.ModelForm):
    class Meta:
        model = PagoVenta
        fields = [
            'fecha',
            'monto',
            'metodo_pago',
            'referencia',
            'observacion',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'observacion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'fecha' in self.fields and not self.initial.get('fecha'):
            self.initial['fecha'] = timezone.now().date()
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto debe ser mayor a 0.')
        return monto
