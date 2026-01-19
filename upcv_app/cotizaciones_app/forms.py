from django import forms
from django.utils import timezone
from django.forms import BaseInlineFormSet, inlineformset_factory

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
            'observaciones',
            'garantia_texto',
            'estado',
        ]
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'garantia_texto': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['fecha_emision'].initial = timezone.now().date()
            self.fields['fecha_emision'].required = False
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing_class} form-control'.strip()


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
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            producto = form.cleaned_data.get("producto_servicio")
            cantidad = form.cleaned_data.get("cantidad")
            if producto and cantidad:
                items_validos += 1
        if items_validos == 0:
            raise forms.ValidationError("Debes agregar al menos un ítem a la cotización.")


CotizacionItemFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionItem,
    form=CotizacionItemForm,
    formset=CotizacionItemInlineFormSet,
    fields=('producto_servicio', 'cantidad'),
    extra=0,
    can_delete=True,
)
