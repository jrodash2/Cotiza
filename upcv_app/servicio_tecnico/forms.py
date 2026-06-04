from django import forms
from django.forms import inlineformset_factory

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
    class Meta:
        model = DetalleCotizacionServicio
        fields = ['tipo_item', 'descripcion', 'cantidad', 'precio_unitario']


DetalleCotizacionFormSet = inlineformset_factory(
    CotizacionServicio,
    DetalleCotizacionServicio,
    form=DetalleCotizacionServicioForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
