from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


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
        if errors:
            raise ValidationError(errors)

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
        totales = self.items.aggregate(
            total_venta=models.Sum('total_linea_venta'),
            total_costo=models.Sum('total_linea_costo'),
            total_ganancia=models.Sum('ganancia_linea'),
        )
        self.subtotal_venta = totales['total_venta'] or Decimal('0.00')
        self.subtotal_costo = totales['total_costo'] or Decimal('0.00')
        self.ganancia_total = totales['total_ganancia'] or Decimal('0.00')
        self.save(update_fields=['subtotal_venta', 'subtotal_costo', 'ganancia_total'])


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
        if self.cantidad <= 0:
            raise ValidationError({'cantidad': 'La cantidad debe ser mayor a 0.'})
        if self.precio_venta_unitario < 0:
            raise ValidationError({'precio_venta_unitario': 'El precio no puede ser negativo.'})
        if self.precio_costo_unitario < 0:
            raise ValidationError({'precio_costo_unitario': 'El precio de costo no puede ser negativo.'})

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
