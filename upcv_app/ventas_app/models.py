from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum

from cotizaciones_app.models import Cliente, Cotizacion


class Articulo(models.Model):
    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Kardex(models.Model):
    TIPO_ENTRADA = 'ENTRADA'
    TIPO_SALIDA = 'SALIDA'
    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SALIDA, 'Salida'),
    ]

    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT, related_name='movimientos_kardex')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    referencia = models.CharField(max_length=120)
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en', '-id']


class VentaCorrelativo(models.Model):
    last_number = models.PositiveIntegerField(default=0)


class Venta(models.Model):
    ESTADO_BORRADOR = 'BORRADOR'
    ESTADO_CONFIRMADA = 'CONFIRMADA'
    ESTADO_ANULADA = 'ANULADA'
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_ANULADA, 'Anulada'),
    ]

    correlativo = models.CharField(max_length=20, unique=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ventas_directas', null=True, blank=True)
    origen_cotizacion = models.ForeignKey(
        Cotizacion,
        on_delete=models.PROTECT,
        related_name='ventas_generadas',
        null=True,
        blank=True,
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas_creadas')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR)
    titulo = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.correlativo

    def _generar_correlativo(self):
        with transaction.atomic():
            correlativo, _ = VentaCorrelativo.objects.select_for_update().get_or_create(id=1)
            correlativo.last_number += 1
            correlativo.save(update_fields=['last_number'])
            return f"V-{correlativo.last_number:04d}"

    def save(self, *args, **kwargs):
        if not self.correlativo:
            self.correlativo = self._generar_correlativo()
        super().save(*args, **kwargs)

    def actualizar_total(self):
        total_articulos = self.detalles_articulos.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        total_servicios = self.detalles_servicios.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        total = total_articulos + total_servicios
        self.total = total
        self.save(update_fields=['total', 'actualizado_en'])

    def clean(self):
        super().clean()
        if self.total < 0:
            raise ValidationError({'total': 'El total no puede ser negativo.'})


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def clean(self):
        super().clean()
        errors = {}
        if self.cantidad <= 0:
            errors['cantidad'] = 'La cantidad debe ser mayor a 0.'
        if self.precio_unitario < 0:
            errors['precio_unitario'] = 'El precio unitario no puede ser negativo.'
        if self.venta.estado != Venta.ESTADO_BORRADOR:
            errors['venta'] = 'Solo puede editar detalles de ventas en borrador.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.subtotal = (self.cantidad or Decimal('0.00')) * (self.precio_unitario or Decimal('0.00'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        venta = self.venta
        super().delete(*args, **kwargs)
        venta.actualizar_total()


class Servicio(models.Model):
    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class _DetalleVentaBase(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        abstract = True
        ordering = ['id']

    def clean(self):
        super().clean()
        errors = {}
        if self.cantidad <= 0:
            errors['cantidad'] = 'La cantidad debe ser mayor a 0.'
        if self.precio_unitario < 0:
            errors['precio_unitario'] = 'El precio unitario no puede ser negativo.'
        if self.venta.estado != Venta.ESTADO_BORRADOR:
            errors['venta'] = 'Solo puede editar detalles de ventas en borrador.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.subtotal = (self.cantidad or Decimal('0.00')) * (self.precio_unitario or Decimal('0.00'))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        venta = self.venta
        super().delete(*args, **kwargs)
        venta.actualizar_total()


class DetalleVentaArticulo(_DetalleVentaBase):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles_articulos')
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        if self.cantidad > self.articulo.stock:
            raise ValidationError({'cantidad': 'La cantidad no puede exceder el stock disponible.'})


class DetalleVentaServicio(_DetalleVentaBase):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles_servicios')
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT)
