from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import (
    PagoOrdenServicio,
    CotizacionServicio,
    DetalleCotizacionServicio,
    OrdenServicio,
    SeguimientoOrdenServicio,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                css = 'form-select'
            else:
                css = 'form-control'
            current_classes = field.widget.attrs.get('class', '').split()
            incompatible_classes = {'form-control', 'form-select', 'form-check-input'}
            classes = [name for name in current_classes if name not in incompatible_classes]
            field.widget.attrs['class'] = ' '.join([*classes, css])
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault('rows', 3)


class OrdenServicioForm(StyledModelForm):
    class Meta:
        model = OrdenServicio
        fields = [
            'cliente', 'tipo_equipo', 'marca', 'modelo', 'numero_serie', 'color',
            'accesorios_entregados', 'estado_fisico', 'falla_reportada',
            'observaciones_recepcion', 'clave_equipo', 'tecnico_asignado',
            'prioridad', 'fecha_estimada_revision', 'diagnostico_final',
            'solucion_aplicada', 'costo_final', 'activo',
        ]
        widgets = {
            'fecha_estimada_revision': forms.DateInput(attrs={'type': 'date'}),
            'costo_final': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00', 'inputmode': 'decimal'}),
        }


class PagoOrdenServicioForm(StyledModelForm):
    class Meta:
        model = PagoOrdenServicio
        fields = ['monto', 'fecha', 'tipo_pago', 'metodo_pago', 'referencia', 'observacion']
        widgets = {
            'monto': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0.00', 'inputmode': 'decimal'}),
            'fecha': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'observacion': forms.Textarea(attrs={'rows': 3}),
        }



class SeguimientoOrdenServicioForm(StyledModelForm):
    class Meta:
        model = SeguimientoOrdenServicio
        fields = ['tipo_seguimiento', 'descripcion']


class CambioEstadoForm(StyledModelForm):
    observacion = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    class Meta:
        model = OrdenServicio
        fields = ['estado']


class EntregaOrdenForm(StyledModelForm):
    class Meta:
        model = OrdenServicio
        fields = ['recibido_por', 'observaciones_entrega']

    def clean_recibido_por(self):
        value = self.cleaned_data['recibido_por'].strip()
        if not value:
            raise forms.ValidationError('Indique el nombre de quien recibe el equipo.')
        return value


class CotizacionServicioForm(StyledModelForm):
    class Meta:
        model = CotizacionServicio
        fields = ['fecha', 'vigencia', 'descuento', 'observaciones', 'estado']
        widgets = {'fecha': forms.DateInput(attrs={'type': 'date'})}


class DetalleCotizacionServicioForm(StyledModelForm):
    campos_contenido = ('descripcion', 'cantidad', 'precio_unitario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('tipo_item', 'descripcion', 'cantidad', 'precio_unitario'):
            self.fields[field_name].required = False

    class Meta:
        model = DetalleCotizacionServicio
        fields = ['tipo_item', 'descripcion', 'cantidad', 'precio_unitario']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0.00', 'inputmode': 'decimal'}),
            'precio_unitario': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00', 'inputmode': 'decimal'}),
        }

    def fila_vacia(self):
        if not self.is_bound or self.instance.pk:
            return False
        id_value = self.data.get(self.add_prefix('id'), '')
        if id_value:
            return False
        tipo_default = DetalleCotizacionServicio.TipoItem.SERVICIO
        tipo_item = self.data.get(self.add_prefix('tipo_item'), '')
        descripcion = self.data.get(self.add_prefix('descripcion'), '').strip()
        cantidad = self.data.get(self.add_prefix('cantidad'), '').strip()
        precio_unitario = self.data.get(self.add_prefix('precio_unitario'), '').strip()
        return (
            not descripcion
            and not precio_unitario
            and cantidad in ('', '1', '1.0', '1.00')
            and tipo_item in ('', tipo_default)
        )

    def has_changed(self):
        if self.fila_vacia():
            return False
        return super().has_changed()

    def clean(self):
        cleaned_data = super().clean()
        if self.fila_vacia() or cleaned_data.get('DELETE'):
            return cleaned_data

        descripcion = cleaned_data.get('descripcion')
        tipo_item = cleaned_data.get('tipo_item')
        cantidad = cleaned_data.get('cantidad')
        precio_unitario = cleaned_data.get('precio_unitario')

        if not descripcion:
            self.add_error('descripcion', 'La descripción es obligatoria para una fila con datos.')
        if not tipo_item:
            self.add_error('tipo_item', 'Seleccione el tipo de ítem.')
        if cantidad is None:
            self.add_error('cantidad', 'Ingrese la cantidad.')
        elif cantidad <= 0:
            self.add_error('cantidad', 'La cantidad debe ser mayor a cero.')
        if precio_unitario is None:
            self.add_error('precio_unitario', 'Ingrese el precio unitario.')
        elif precio_unitario < 0:
            self.add_error('precio_unitario', 'El precio no puede ser negativo.')
        return cleaned_data


class BaseDetalleCotizacionFormSet(BaseInlineFormSet):
    def save_new_objects(self, commit=True):
        self.new_objects = []
        for form in self.extra_forms:
            if not form.has_changed() or self._should_delete_form(form):
                continue
            self.new_objects.append(self.save_new(form, commit=commit))
        return self.new_objects


DetalleCotizacionFormSet = inlineformset_factory(
    CotizacionServicio,
    DetalleCotizacionServicio,
    form=DetalleCotizacionServicioForm,
    formset=BaseDetalleCotizacionFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
