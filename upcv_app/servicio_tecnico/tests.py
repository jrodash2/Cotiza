from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from cotizaciones_app.models import Cliente
from .models import CotizacionServicio, DetalleCotizacionServicio, OrdenServicio


class ServicioTecnicoModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='admin-test', password='test')
        self.cliente = Cliente.objects.create(nombre='Cliente de prueba')

    def test_orden_genera_correlativo_e_historial(self):
        orden = OrdenServicio.objects.create(cliente=self.cliente, tipo_equipo='Laptop', falla_reportada='No enciende', usuario_creacion=self.user)
        self.assertRegex(orden.numero_orden, r'^OS-\d{4}-\d{5}$')
        self.assertEqual(orden.historial_estados.count(), 1)
        orden.estado = OrdenServicio.Estado.EN_DIAGNOSTICO
        orden.save(usuario_historial=self.user, observacion_historial='Inicia revisión')
        self.assertEqual(orden.historial_estados.first().estado_nuevo, OrdenServicio.Estado.EN_DIAGNOSTICO)

    def test_detalle_recalcula_totales(self):
        orden = OrdenServicio.objects.create(cliente=self.cliente, tipo_equipo='Laptop', falla_reportada='No enciende', usuario_creacion=self.user)
        cotizacion = CotizacionServicio.objects.create(orden_servicio=orden, descuento=Decimal('10.00'), usuario_creacion=self.user)
        DetalleCotizacionServicio.objects.create(cotizacion=cotizacion, descripcion='Repuesto', cantidad=2, precio_unitario=Decimal('50.00'))
        cotizacion.refresh_from_db()
        self.assertEqual(cotizacion.subtotal, Decimal('100.00'))
        self.assertEqual(cotizacion.total, Decimal('90.00'))

    def test_anticipo_no_puede_ser_negativo_ni_superar_costo_final(self):
        orden = OrdenServicio(
            cliente=self.cliente,
            tipo_equipo='Laptop',
            falla_reportada='No enciende',
            usuario_creacion=self.user,
            costo_final=Decimal('100.00'),
            anticipo=Decimal('120.00'),
        )
        with self.assertRaisesMessage(ValidationError, 'El anticipo no puede superar el costo final registrado.'):
            orden.full_clean()

    def test_anticipo_no_puede_ser_negativo(self):
        orden = OrdenServicio(
            cliente=self.cliente,
            tipo_equipo='Laptop',
            falla_reportada='No enciende',
            usuario_creacion=self.user,
            anticipo=Decimal('-1.00'),
        )
        with self.assertRaisesMessage(ValidationError, 'El anticipo no puede ser negativo.'):
            orden.full_clean()

    def test_saldo_pendiente_nunca_es_negativo(self):
        orden = OrdenServicio(costo_final=Decimal('50.00'), anticipo=Decimal('75.00'))
        self.assertEqual(orden.saldo_pendiente, Decimal('0.00'))


class ServicioTecnicoFormTests(TestCase):
    def test_activo_usa_checkbox_bootstrap_y_anticipo_widget_monetario(self):
        from .forms import OrdenServicioForm

        form = OrdenServicioForm()
        self.assertEqual(form.fields['activo'].widget.input_type, 'checkbox')
        self.assertIn('form-check-input', form.fields['activo'].widget.attrs['class'])
        self.assertNotIn('form-control', form.fields['activo'].widget.attrs['class'])
        self.assertEqual(form.fields['anticipo'].widget.attrs['step'], '0.01')
        self.assertEqual(form.fields['anticipo'].widget.attrs['min'], '0')
