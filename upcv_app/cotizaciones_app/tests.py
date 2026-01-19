from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cliente, Cotizacion, CotizacionItem, ProductoServicio


class CotizacionUpdateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='tester', password='password')
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(nombre='Cliente Demo')
        self.producto_a = ProductoServicio.objects.create(
            tipo=ProductoServicio.TIPO_PRODUCTO,
            nombre='Producto A',
            descripcion='Desc A',
            unidad='Unidad',
            precio_costo=Decimal('10.00'),
            precio_venta=Decimal('20.00'),
        )
        self.producto_b = ProductoServicio.objects.create(
            tipo=ProductoServicio.TIPO_PRODUCTO,
            nombre='Producto B',
            descripcion='Desc B',
            unidad='Unidad',
            precio_costo=Decimal('15.00'),
            precio_venta=Decimal('30.00'),
        )
        self.cotizacion = Cotizacion.objects.create(
            fecha_emision=timezone.now().date(),
            cliente=self.cliente,
            titulo='Titulo',
            validez_dias=15,
            observaciones='',
            garantia_texto='GARANTIA',
            estado=Cotizacion.ESTADO_BORRADOR,
        )
        self.item = CotizacionItem.objects.create(
            cotizacion=self.cotizacion,
            producto_servicio=self.producto_a,
            cantidad=Decimal('1.00'),
            precio_venta_unitario=self.producto_a.precio_venta,
            precio_costo_unitario=self.producto_a.precio_costo,
        )

    def _base_form_data(self):
        return {
            'fecha_emision': self.cotizacion.fecha_emision.isoformat(),
            'cliente': str(self.cliente.id),
            'titulo': self.cotizacion.titulo,
            'validez_dias': str(self.cotizacion.validez_dias),
            'observaciones': self.cotizacion.observaciones,
            'garantia_texto': self.cotizacion.garantia_texto,
            'estado': self.cotizacion.estado,
        }

    def test_update_existing_item_persists(self):
        url = reverse('cotizaciones:cotizacion_update', args=[self.cotizacion.pk])
        data = {
            **self._base_form_data(),
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': str(self.item.id),
            'items-0-producto_servicio': str(self.producto_a.id),
            'items-0-cantidad': '2.00',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.cantidad, Decimal('2.00'))

    def test_add_new_item_persists(self):
        url = reverse('cotizaciones:cotizacion_update', args=[self.cotizacion.pk])
        data = {
            **self._base_form_data(),
            'items-TOTAL_FORMS': '2',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': str(self.item.id),
            'items-0-producto_servicio': str(self.producto_a.id),
            'items-0-cantidad': '1.00',
            'items-1-id': '',
            'items-1-producto_servicio': str(self.producto_b.id),
            'items-1-cantidad': '3.00',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.cotizacion.items.count(), 2)
        nuevo_item = self.cotizacion.items.order_by('-id').first()
        self.assertEqual(nuevo_item.producto_servicio_id, self.producto_b.id)

    def test_delete_item_persists(self):
        url = reverse('cotizaciones:cotizacion_update', args=[self.cotizacion.pk])
        data = {
            **self._base_form_data(),
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': str(self.item.id),
            'items-0-producto_servicio': str(self.producto_a.id),
            'items-0-cantidad': '1.00',
            'items-0-DELETE': 'on',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CotizacionItem.objects.filter(id=self.item.id).exists())


class CotizacionCreateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='creator', password='password')
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(nombre='Cliente Create')
        self.producto = ProductoServicio.objects.create(
            tipo=ProductoServicio.TIPO_PRODUCTO,
            nombre='Producto C',
            descripcion='Desc C',
            unidad='Unidad',
            precio_costo=Decimal('5.00'),
            precio_venta=Decimal('12.00'),
        )

    def test_create_cotizacion_with_item(self):
        url = reverse('cotizaciones:cotizacion_create')
        data = {
            'cliente': str(self.cliente.id),
            'titulo': 'Nueva',
            'validez_dias': '15',
            'observaciones': '',
            'garantia_texto': 'GARANTIA',
            'estado': Cotizacion.ESTADO_BORRADOR,
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': '',
            'items-0-producto_servicio': str(self.producto.id),
            'items-0-cantidad': '1.00',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Cotizacion.objects.count(), 1)
        self.assertEqual(CotizacionItem.objects.count(), 1)
        item = CotizacionItem.objects.first()
        self.assertEqual(item.precio_venta_unitario, self.producto.precio_venta)
