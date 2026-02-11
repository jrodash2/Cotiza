import calendar
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone


def add_months(date_value, months):
    if not date_value:
        return None
    month = date_value.month - 1 + months
    year = date_value.year + month // 12
    month = month % 12 + 1
    day = min(date_value.day, calendar.monthrange(year, month)[1])
    return date_value.replace(year=year, month=month, day=day)


class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    contacto = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    nit = models.CharField(max_length=50, blank=True)
    municipio = models.CharField(max_length=100, blank=True)
    departamento = models.CharField(max_length=100, blank=True)
    notas = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.nombre


class ProductoServicio(models.Model):
    TIPO_PRODUCTO = 'PRODUCTO'
    TIPO_SERVICIO = 'SERVICIO'
    TIPO_CHOICES = [
        (TIPO_PRODUCTO, 'Producto'),
        (TIPO_SERVICIO, 'Servicio'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    unidad = models.CharField(max_length=50, blank=True)
    precio_costo = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.nombre

    def clean(self) -> None:
        if self.precio_costo < 0:
            raise ValidationError({'precio_costo': 'El precio de costo no puede ser negativo.'})
        if self.precio_venta < 0:
            raise ValidationError({'precio_venta': 'El precio no puede ser negativo.'})


class CotizacionCorrelativo(models.Model):
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"Correlativo actual: {self.last_number}"


class Cotizacion(models.Model):
    ESTADO_BORRADOR = 'BORRADOR'
    ESTADO_EMITIDA = 'EMITIDA'
    ESTADO_ANULADA = 'ANULADA'
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_EMITIDA, 'Emitida'),
        (ESTADO_ANULADA, 'Anulada'),
    ]

    correlativo = models.CharField(max_length=5, unique=True, blank=True)
    fecha_emision = models.DateField(default=timezone.now)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='cotizaciones')
    titulo = models.CharField(max_length=255, blank=True)
    validez_dias = models.PositiveIntegerField(default=15)
    observaciones = models.TextField(blank=True)
    garantia_texto = models.CharField(
        max_length=255,
        default='GARANTIA DE 6 MESES EN EQUIPOS E INSTALACIÓN',
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR)
    subtotal_venta = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    subtotal_costo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    ganancia_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    descuento_monto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('12.00'), blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
    total_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
    total_iva = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
    precios_sin_iva = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_emision', '-id']

    def __str__(self) -> str:
        return f"{self.correlativo} - {self.cliente}"

    def clean(self) -> None:
        super().clean()
        errors = {}
        if self.validez_dias is not None and self.validez_dias < 1:
            errors['validez_dias'] = 'La validez debe ser mayor a 0.'
        if self.subtotal_venta is not None and self.subtotal_venta < 0:
            errors['subtotal_venta'] = 'El subtotal no puede ser negativo.'
        if self.subtotal_costo is not None and self.subtotal_costo < 0:
            errors['subtotal_costo'] = 'El subtotal no puede ser negativo.'
        if self.ganancia_total is not None and self.ganancia_total < 0:
            errors['ganancia_total'] = 'La ganancia no puede ser negativa.'
        if self.descuento_monto is not None and self.descuento_monto < 0:
            errors['descuento_monto'] = 'El descuento fijo no puede ser negativo.'
        if self.descuento_porcentaje is not None and self.descuento_porcentaje < 0:
            errors['descuento_porcentaje'] = 'El descuento porcentual no puede ser negativo.'
        if self.iva_porcentaje is not None and self.iva_porcentaje < 0:
            errors['iva_porcentaje'] = 'El IVA no puede ser negativo.'
        if errors:
            raise ValidationError(errors)


    @property
    def base_imponible(self):
        base = (self.subtotal or Decimal('0.00')) - (self.total_descuento or Decimal('0.00'))
        return base if base > Decimal('0.00') else Decimal('0.00')

    def _generar_correlativo(self) -> str:
        with transaction.atomic():
            correlativo, _ = CotizacionCorrelativo.objects.select_for_update().get_or_create(id=1)
            correlativo.last_number += 1
            correlativo.save(update_fields=['last_number'])
            return f"{correlativo.last_number:05d}"

    def save(self, *args, **kwargs):
        if not self.correlativo:
            self.correlativo = self._generar_correlativo()
        super().save(*args, **kwargs)

    def actualizar_totales(self) -> None:
        self.recalcular_totales(save=True)

    def recalcular_totales(self, save=False) -> None:
        totales = self.items.aggregate(
            total_venta=models.Sum('total_linea_venta'),
            total_costo=models.Sum('total_linea_costo'),
            total_ganancia=models.Sum('ganancia_linea'),
        )
        decimal_cero = Decimal('0.00')
        porcentaje_cien = Decimal('100.00')
        subtotal_items = totales['total_venta'] or decimal_cero

        self.subtotal_venta = subtotal_items
        self.subtotal_costo = totales['total_costo'] or decimal_cero
        self.ganancia_total = totales['total_ganancia'] or decimal_cero
        self.subtotal = subtotal_items

        descuento_porcentaje = self.descuento_porcentaje or decimal_cero
        descuento_monto = self.descuento_monto or decimal_cero
        iva_porcentaje = self.iva_porcentaje or decimal_cero

        if descuento_porcentaje > decimal_cero:
            self.total_descuento = subtotal_items * (descuento_porcentaje / porcentaje_cien)
        else:
            self.total_descuento = descuento_monto

        base_imponible = subtotal_items - self.total_descuento
        if base_imponible < decimal_cero:
            base_imponible = decimal_cero

        if self.precios_sin_iva:
            self.total_iva = base_imponible * (iva_porcentaje / porcentaje_cien)
        else:
            self.total_iva = decimal_cero

        self.total = base_imponible + self.total_iva

        if save:
            self.save(
                update_fields=[
                    'subtotal_venta',
                    'subtotal_costo',
                    'ganancia_total',
                    'subtotal',
                    'total_descuento',
                    'total_iva',
                    'total',
                ]
            )


class CotizacionItem(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='items')
    producto_servicio = models.ForeignKey(ProductoServicio, on_delete=models.PROTECT)
    descripcion_editable = models.TextField(blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    precio_venta_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    precio_costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    total_linea_venta = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_linea_costo = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    ganancia_linea = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self) -> str:
        return f"{self.cotizacion.correlativo} - {self.producto_servicio.nombre}"

    def clean(self) -> None:
        super().clean()
        errors = {}
        if self.cantidad is not None and self.cantidad <= 0:
            errors['cantidad'] = 'La cantidad debe ser mayor a 0.'
        if self.precio_venta_unitario is not None and self.precio_venta_unitario < 0:
            errors['precio_venta_unitario'] = 'El precio no puede ser negativo.'
        if self.precio_costo_unitario is not None and self.precio_costo_unitario < 0:
            errors['precio_costo_unitario'] = 'El precio de costo no puede ser negativo.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.total_linea_venta = (self.cantidad or Decimal('0.00')) * (self.precio_venta_unitario or Decimal('0.00'))
        self.total_linea_costo = (self.cantidad or Decimal('0.00')) * (self.precio_costo_unitario or Decimal('0.00'))
        self.ganancia_linea = self.total_linea_venta - self.total_linea_costo
        super().save(*args, **kwargs)
        self.cotizacion.actualizar_totales()

    def delete(self, *args, **kwargs):
        cotizacion = self.cotizacion
        super().delete(*args, **kwargs)
        cotizacion.actualizar_totales()


class Venta(models.Model):
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_PARCIAL = 'PARCIAL'
    ESTADO_PAGADA = 'PAGADA'
    ESTADO_PAGO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_PARCIAL, 'Parcial'),
        (ESTADO_PAGADA, 'Pagada'),
    ]

    cotizacion = models.OneToOneField(
        Cotizacion,
        on_delete=models.PROTECT,
        related_name='venta',
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ventas')
    fecha_venta = models.DateField(default=timezone.now)
    estado_pago = models.CharField(
        max_length=20,
        choices=ESTADO_PAGO_CHOICES,
        default=ESTADO_PENDIENTE,
    )
    fecha_pago_total = models.DateField(blank=True, null=True)
    fecha_inicio_garantia = models.DateField(blank=True, null=True)
    fecha_fin_garantia = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_venta', '-id']

    def __str__(self) -> str:
        return f"Venta {self.id} - {self.cliente}"

    @property
    def total(self):
        return self.cotizacion.subtotal_venta or Decimal('0.00')

    @property
    def total_pagado(self):
        total = self.pagos.aggregate(total=models.Sum('monto'))['total']
        return total or Decimal('0.00')

    @property
    def saldo(self):
        return self.total - self.total_pagado

    @property
    def porcentaje_avance(self):
        total = self.total
        if total <= 0:
            return Decimal('0.00')
        return (self.total_pagado / total) * Decimal('100')

    def actualizar_estado_pago(self, save=True):
        total = self.total
        pagado = self.total_pagado
        if total <= 0:
            estado = self.ESTADO_PENDIENTE
        elif pagado >= total:
            estado = self.ESTADO_PAGADA
        elif pagado > 0:
            estado = self.ESTADO_PARCIAL
        else:
            estado = self.ESTADO_PENDIENTE

        self.estado_pago = estado
        if estado == self.ESTADO_PAGADA:
            if not self.fecha_pago_total:
                self.fecha_pago_total = timezone.now().date()
            if not self.fecha_inicio_garantia:
                self.fecha_inicio_garantia = self.fecha_pago_total
            if not self.fecha_fin_garantia and self.fecha_inicio_garantia:
                self.fecha_fin_garantia = add_months(self.fecha_inicio_garantia, 6)
        if save:
            self.save(
                update_fields=[
                    'estado_pago',
                    'fecha_pago_total',
                    'fecha_inicio_garantia',
                    'fecha_fin_garantia',
                ]
            )


class PagoVenta(models.Model):
    METODO_TRANSFERENCIA = 'TRANSFERENCIA'
    METODO_EFECTIVO = 'EFECTIVO'
    METODO_TARJETA = 'TARJETA'
    METODO_OTRO = 'OTRO'
    METODO_PAGO_CHOICES = [
        (METODO_TRANSFERENCIA, 'Transferencia'),
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TARJETA, 'Tarjeta'),
        (METODO_OTRO, 'Otro'),
    ]

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos')
    fecha = models.DateField(default=timezone.now)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    correlativo_comprobante = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self) -> str:
        return f"Pago {self.id} - Venta {self.venta_id}"

    def clean(self) -> None:
        super().clean()
        if self.monto is not None and self.monto <= 0:
            raise ValidationError({'monto': 'El monto debe ser mayor a 0.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.correlativo_comprobante:
                last_number = (
                    PagoVenta.objects.filter(venta=self.venta)
                    .aggregate(max_num=Max('correlativo_comprobante'))
                    .get('max_num')
                )
                self.correlativo_comprobante = (last_number or 0) + 1
            super().save(*args, **kwargs)
            self.venta.actualizar_estado_pago()

    def delete(self, *args, **kwargs):
        venta = self.venta
        super().delete(*args, **kwargs)
        venta.actualizar_estado_pago()
