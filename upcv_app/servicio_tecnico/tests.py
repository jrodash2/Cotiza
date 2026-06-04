from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from cotizaciones_app.models import Cliente
from .forms import DetalleCotizacionFormSet, OrdenServicioForm
from .models import AnticipoOrdenServicio, CotizacionServicio, DetalleCotizacionServicio, OrdenServicio


class ServicioTecnicoModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='admin-test', password='test')
        self.cliente = Cliente.objects.create(nombre='Cliente de prueba')
        self.orden = OrdenServicio.objects.create(
            cliente=self.cliente,
            tipo_equipo='Laptop',
            falla_reportada='No enciende',
            usuario_creacion=self.user,
        )

    def test_orden_genera_correlativo_e_historial(self):
        self.assertRegex(self.orden.numero_orden, r'^OS-\d{4}-\d{5}$')
        self.assertEqual(self.orden.historial_estados.count(), 1)
        self.orden.estado = OrdenServicio.Estado.EN_DIAGNOSTICO
        self.orden.save(usuario_historial=self.user, observacion_historial='Inicia revisión')
        self.assertEqual(self.orden.historial_estados.first().estado_nuevo, OrdenServicio.Estado.EN_DIAGNOSTICO)

    def test_detalle_recalcula_totales_y_eliminacion_actualiza_total(self):
        cotizacion = CotizacionServicio.objects.create(orden_servicio=self.orden, descuento=Decimal('10.00'), usuario_creacion=self.user)
        detalle = DetalleCotizacionServicio.objects.create(cotizacion=cotizacion, descripcion='Repuesto', cantidad=2, precio_unitario=Decimal('50.00'))
        cotizacion.refresh_from_db()
        self.assertEqual(cotizacion.total, Decimal('90.00'))
        detalle.delete()
        cotizacion.refresh_from_db()
        self.assertEqual(cotizacion.total, Decimal('0.00'))

    def test_anticipo_solo_se_permite_con_reparacion_aprobada(self):
        anticipo = AnticipoOrdenServicio(orden_servicio=self.orden, monto=Decimal('25.00'), usuario=self.user)
        with self.assertRaisesMessage(ValidationError, 'Solo se pueden registrar anticipos cuando la reparación está aprobada.'):
            anticipo.full_clean()

    def test_anticipos_acumulados_no_superan_total_aprobado(self):
        CotizacionServicio.objects.create(
            orden_servicio=self.orden,
            total=Decimal('100.00'),
            estado=CotizacionServicio.Estado.APROBADA,
            usuario_creacion=self.user,
        )
        self.orden.estado = OrdenServicio.Estado.APROBADO_REPARACION
        self.orden.save(usuario_historial=self.user)
        AnticipoOrdenServicio.objects.create(orden_servicio=self.orden, monto=Decimal('60.00'), usuario=self.user)
        segundo = AnticipoOrdenServicio(orden_servicio=self.orden, monto=Decimal('50.00'), usuario=self.user)
        with self.assertRaisesMessage(ValidationError, 'El total de anticipos no puede superar el total aprobado.'):
            segundo.full_clean()
        self.assertEqual(self.orden.total_anticipos, Decimal('60.00'))
        self.assertEqual(self.orden.saldo_pendiente, Decimal('40.00'))

    def test_anticipo_debe_ser_mayor_a_cero(self):
        self.orden.estado = OrdenServicio.Estado.APROBADO_REPARACION
        self.orden.save(usuario_historial=self.user)
        anticipo = AnticipoOrdenServicio(orden_servicio=self.orden, monto=Decimal('-1.00'), usuario=self.user)
        with self.assertRaisesMessage(ValidationError, 'El anticipo debe ser mayor a cero.'):
            anticipo.full_clean()


class ServicioTecnicoFormTests(TestCase):
    def test_orden_no_solicita_anticipo_y_activo_usa_checkbox_bootstrap(self):
        form = OrdenServicioForm()
        self.assertNotIn('anticipo', form.fields)
        self.assertEqual(form.fields['activo'].widget.input_type, 'checkbox')
        self.assertIn('form-check-input', form.fields['activo'].widget.attrs['class'])
        self.assertNotIn('form-control', form.fields['activo'].widget.attrs['class'])

    def test_formset_elimina_existente_y_acepta_nuevo_item(self):
        user = get_user_model().objects.create_user(username='formset-user')
        cliente = Cliente.objects.create(nombre='Cliente formset')
        orden = OrdenServicio.objects.create(cliente=cliente, tipo_equipo='PC', falla_reportada='Falla', usuario_creacion=user)
        cotizacion = CotizacionServicio.objects.create(orden_servicio=orden, usuario_creacion=user)
        detalle = DetalleCotizacionServicio.objects.create(cotizacion=cotizacion, descripcion='Anterior', cantidad=1, precio_unitario=Decimal('10.00'))
        data = {
            'detalles-TOTAL_FORMS': '2', 'detalles-INITIAL_FORMS': '1', 'detalles-MIN_NUM_FORMS': '1', 'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-id': str(detalle.pk), 'detalles-0-tipo_item': 'SERVICIO', 'detalles-0-descripcion': 'Anterior', 'detalles-0-cantidad': '1', 'detalles-0-precio_unitario': '10', 'detalles-0-DELETE': 'on',
            'detalles-1-id': '', 'detalles-1-tipo_item': 'MANO_OBRA', 'detalles-1-descripcion': 'Nueva línea', 'detalles-1-cantidad': '2', 'detalles-1-precio_unitario': '25',
        }
        formset = DetalleCotizacionFormSet(data, instance=cotizacion)
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertFalse(cotizacion.detalles.filter(pk=detalle.pk).exists())
        self.assertEqual(cotizacion.detalles.get().descripcion, 'Nueva línea')
        cotizacion.refresh_from_db()
        self.assertEqual(cotizacion.total, Decimal('50.00'))
