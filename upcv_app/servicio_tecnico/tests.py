from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from cotizaciones_app.models import Cliente
from .forms import DetalleCotizacionFormSet, OrdenServicioForm
from .models import CotizacionServicio, DetalleCotizacionServicio, OrdenServicio, PagoOrdenServicio
from .utils import nombre_usuario


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

    def test_detalle_clean_maneja_valores_nulos_sin_type_error(self):
        cotizacion = CotizacionServicio.objects.create(orden_servicio=self.orden, usuario_creacion=self.user)
        detalle = DetalleCotizacionServicio(cotizacion=cotizacion, cantidad=None, precio_unitario=None)
        with self.assertRaises(ValidationError) as context:
            detalle.full_clean()
        self.assertIn('cantidad', context.exception.message_dict)
        self.assertIn('precio_unitario', context.exception.message_dict)

    def aprobar_orden_con_total(self, total=Decimal('100.00')):
        CotizacionServicio.objects.create(
            orden_servicio=self.orden,
            total=total,
            estado=CotizacionServicio.Estado.APROBADA,
            usuario_creacion=self.user,
        )
        self.orden.estado = OrdenServicio.Estado.APROBADO_REPARACION
        self.orden.save(usuario_historial=self.user)

    def test_pago_requiere_estado_permitido_y_total_definido(self):
        pago = PagoOrdenServicio(orden_servicio=self.orden, monto=Decimal('25.00'), usuario_registro=self.user)
        with self.assertRaisesMessage(ValidationError, 'La orden no se encuentra en un estado que permita registrar pagos.'):
            pago.full_clean()
        self.orden.estado = OrdenServicio.Estado.APROBADO_REPARACION
        self.orden.save(usuario_historial=self.user)
        with self.assertRaisesMessage(ValidationError, 'Debe existir un costo final o una cotización aprobada antes de registrar pagos.'):
            pago.full_clean()

    def test_pagos_parciales_y_pago_despues_de_entrega(self):
        self.aprobar_orden_con_total()
        PagoOrdenServicio.objects.create(orden_servicio=self.orden, monto=Decimal('30.00'), tipo_pago='ANTICIPO', usuario_registro=self.user)
        self.assertEqual(self.orden.anticipo_total, Decimal('30.00'))
        self.assertEqual(self.orden.estado_pago, 'PAGO_PARCIAL')
        self.orden.estado = OrdenServicio.Estado.ENTREGADO
        self.orden.fecha_entrega = self.orden.fecha_recepcion
        self.orden.save(usuario_historial=self.user)
        PagoOrdenServicio.objects.create(orden_servicio=self.orden, monto=Decimal('70.00'), tipo_pago='PAGO_FINAL', usuario_registro=self.user)
        self.assertEqual(self.orden.total_pagado, Decimal('100.00'))
        self.assertEqual(self.orden.saldo_pendiente, Decimal('0.00'))
        self.assertTrue(self.orden.esta_pagada)
        self.assertEqual(self.orden.estado_pago, 'PAGADO')
        self.assertRegex(self.orden.pagos.first().numero_recibo, r'^REC-\d{4}-\d{5}$')

    def test_pago_no_supera_saldo_y_costo_final_manda(self):
        self.aprobar_orden_con_total(Decimal('100.00'))
        self.orden.costo_final = Decimal('80.00')
        self.orden.save()
        PagoOrdenServicio.objects.create(orden_servicio=self.orden, monto=Decimal('60.00'), usuario_registro=self.user)
        segundo = PagoOrdenServicio(orden_servicio=self.orden, monto=Decimal('25.00'), usuario_registro=self.user)
        with self.assertRaisesMessage(ValidationError, 'El pago no puede superar el saldo pendiente.'):
            segundo.full_clean()
        self.assertEqual(self.orden.total_cobro, Decimal('80.00'))
        self.assertEqual(self.orden.saldo_pendiente, Decimal('20.00'))
        self.orden.costo_final = Decimal('50.00')
        with self.assertRaisesMessage(ValidationError, 'El costo final no puede ser menor que el total pagado.'):
            self.orden.full_clean()

    def test_pago_debe_ser_mayor_a_cero_y_anulado_no_suma(self):
        self.aprobar_orden_con_total()
        pago = PagoOrdenServicio(orden_servicio=self.orden, monto=Decimal('-1.00'), usuario_registro=self.user)
        with self.assertRaisesMessage(ValidationError, 'El pago debe ser mayor a cero.'):
            pago.full_clean()
        pago = PagoOrdenServicio.objects.create(orden_servicio=self.orden, monto=Decimal('20.00'), usuario_registro=self.user)
        pago.activo = False
        pago.save()
        self.assertEqual(self.orden.total_pagado, Decimal('0.00'))


class ServicioTecnicoFormTests(TestCase):
    def test_orden_no_solicita_pago_y_activo_usa_checkbox_bootstrap(self):
        form = OrdenServicioForm()
        self.assertNotIn('pago', form.fields)
        self.assertEqual(form.fields['activo'].widget.input_type, 'checkbox')
        self.assertIn('form-check-input', form.fields['activo'].widget.attrs['class'])
        self.assertNotIn('form-control', form.fields['activo'].widget.attrs['class'])

    def test_nombre_usuario_prefiere_nombre_completo_y_usa_username_como_fallback(self):
        user = get_user_model().objects.create_user(
            username='tecnico-fallback',
            first_name='Ana',
            last_name='García',
        )
        self.assertEqual(nombre_usuario(user), 'Ana García')
        user.last_name = ''
        self.assertEqual(nombre_usuario(user), 'Ana')
        user.first_name = ''
        self.assertEqual(nombre_usuario(user), 'tecnico-fallback')

    def test_tecnico_asignado_muestra_nombre_legible_en_formulario(self):
        tecnico = get_user_model().objects.create_user(
            username='tecnico-form',
            first_name='Luis',
            last_name='Pérez',
        )
        form = OrdenServicioForm()
        self.assertEqual(form.fields['tecnico_asignado'].label_from_instance(tecnico), 'Luis Pérez')

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

    def test_formset_ignora_fila_extra_vacia_con_valores_por_defecto(self):
        user = get_user_model().objects.create_user(username='formset-empty-user')
        cliente = Cliente.objects.create(nombre='Cliente formset vacío')
        orden = OrdenServicio.objects.create(cliente=cliente, tipo_equipo='PC', falla_reportada='Falla', usuario_creacion=user)
        cotizacion = CotizacionServicio.objects.create(orden_servicio=orden, usuario_creacion=user)
        data = {
            'detalles-TOTAL_FORMS': '2', 'detalles-INITIAL_FORMS': '0', 'detalles-MIN_NUM_FORMS': '1', 'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-id': '', 'detalles-0-tipo_item': 'SERVICIO', 'detalles-0-descripcion': 'Diagnóstico', 'detalles-0-cantidad': '1', 'detalles-0-precio_unitario': '25',
            'detalles-1-id': '', 'detalles-1-tipo_item': 'SERVICIO', 'detalles-1-descripcion': '', 'detalles-1-cantidad': '1.00', 'detalles-1-precio_unitario': '',
        }
        formset = DetalleCotizacionFormSet(data, instance=cotizacion)
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertEqual(cotizacion.detalles.count(), 1)
        self.assertEqual(cotizacion.detalles.get().descripcion, 'Diagnóstico')

    def test_formset_marca_error_en_fila_parcial(self):
        user = get_user_model().objects.create_user(username='formset-partial-user')
        cliente = Cliente.objects.create(nombre='Cliente formset parcial')
        orden = OrdenServicio.objects.create(cliente=cliente, tipo_equipo='PC', falla_reportada='Falla', usuario_creacion=user)
        cotizacion = CotizacionServicio.objects.create(orden_servicio=orden, usuario_creacion=user)
        data = {
            'detalles-TOTAL_FORMS': '1', 'detalles-INITIAL_FORMS': '0', 'detalles-MIN_NUM_FORMS': '1', 'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-id': '', 'detalles-0-tipo_item': 'SERVICIO', 'detalles-0-descripcion': 'Diagnóstico', 'detalles-0-cantidad': '1', 'detalles-0-precio_unitario': '',
        }
        formset = DetalleCotizacionFormSet(data, instance=cotizacion)
        self.assertFalse(formset.is_valid())
        self.assertIn('precio_unitario', formset.forms[0].errors)
