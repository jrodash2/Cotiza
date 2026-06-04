from decimal import Decimal

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone


class CorrelativoServicio(models.Model):
    tipo = models.CharField(max_length=20)
    anio = models.PositiveSmallIntegerField()
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['tipo', 'anio'], name='servicio_correlativo_tipo_anio')]

    @classmethod
    def siguiente(cls, tipo, prefijo):
        anio = timezone.localdate().year
        with transaction.atomic():
            correlativo, _ = cls.objects.select_for_update().get_or_create(tipo=tipo, anio=anio)
            correlativo.ultimo_numero += 1
            correlativo.save(update_fields=['ultimo_numero'])
        return f'{prefijo}-{anio}-{correlativo.ultimo_numero:05d}'


class OrdenServicio(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = 'BAJA', 'Baja'
        NORMAL = 'NORMAL', 'Normal'
        ALTA = 'ALTA', 'Alta'
        URGENTE = 'URGENTE', 'Urgente'

    class Estado(models.TextChoices):
        RECIBIDO = 'RECIBIDO', 'Recibido'
        EN_DIAGNOSTICO = 'EN_DIAGNOSTICO', 'En diagnóstico'
        PENDIENTE_COTIZACION = 'PENDIENTE_COTIZACION', 'Pendiente de cotización'
        COTIZADO = 'COTIZADO', 'Cotizado'
        APROBADO_REPARACION = 'APROBADO_REPARACION', 'Aprobado para reparación'
        EN_REPARACION = 'EN_REPARACION', 'En reparación'
        PENDIENTE_REPUESTO = 'PENDIENTE_REPUESTO', 'Pendiente de repuesto'
        REPARADO = 'REPARADO', 'Reparado'
        LISTO_PARA_ENTREGAR = 'LISTO_PARA_ENTREGAR', 'Listo para entregar'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        NO_REPARADO = 'NO_REPARADO', 'No reparado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    numero_orden = models.CharField(max_length=20, unique=True, blank=True)
    cliente = models.ForeignKey('cotizaciones_app.Cliente', on_delete=models.PROTECT, related_name='ordenes_servicio')
    tipo_equipo = models.CharField(max_length=100)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=120, blank=True)
    color = models.CharField(max_length=80, blank=True)
    accesorios_entregados = models.TextField(blank=True)
    estado_fisico = models.TextField(blank=True)
    falla_reportada = models.TextField()
    observaciones_recepcion = models.TextField(blank=True)
    clave_equipo = models.CharField(max_length=255, blank=True, help_text='Dato confidencial; mostrar únicamente a personal autorizado.')
    tecnico_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_tecnicas')
    prioridad = models.CharField(max_length=12, choices=Prioridad.choices, default=Prioridad.NORMAL)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.RECIBIDO)
    fecha_recepcion = models.DateTimeField(default=timezone.now)
    fecha_estimada_revision = models.DateField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    diagnostico_final = models.TextField(blank=True)
    solucion_aplicada = models.TextField(blank=True)
    costo_final = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    recibido_por = models.CharField(max_length=200, blank=True)
    observaciones_entrega = models.TextField(blank=True)
    usuario_creacion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ordenes_servicio_creadas')
    activo = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_recepcion', '-id']
        permissions = [
            ('gestionar_recepcion', 'Puede gestionar recepción de equipos'),
            ('gestionar_tecnica', 'Puede gestionar seguimiento técnico'),
            ('gestionar_entrega', 'Puede registrar entrega de equipos'),
        ]

    def __str__(self):
        return f'{self.numero_orden} - {self.cliente}'

    def get_absolute_url(self):
        return reverse('servicio_tecnico:orden_detalle', kwargs={'pk': self.pk})

    def clean(self):
        errors = {}
        if self.costo_final is not None and self.costo_final < 0:
            errors['costo_final'] = 'El costo final no puede ser negativo.'
        if self.estado == self.Estado.ENTREGADO and not self.fecha_entrega:
            errors['fecha_entrega'] = 'Debe registrar la fecha de entrega.'
        if errors:
            raise ValidationError(errors)

    @property
    def cotizacion_aprobada(self):
        return self.cotizaciones_servicio.filter(estado=CotizacionServicio.Estado.APROBADA).order_by('-fecha', '-id').first()

    @property
    def total_aprobado(self):
        cotizacion = self.cotizacion_aprobada
        return cotizacion.total if cotizacion else (self.costo_final or Decimal('0.00'))

    @property
    def total_anticipos(self):
        return self.anticipos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    @property
    def saldo_pendiente(self):
        return max(self.total_aprobado - self.total_anticipos, Decimal('0.00'))

    def save(self, *args, **kwargs):
        usuario_historial = kwargs.pop('usuario_historial', None)
        observacion_historial = kwargs.pop('observacion_historial', '')
        estado_anterior = None
        if self.pk:
            estado_anterior = type(self).objects.filter(pk=self.pk).values_list('estado', flat=True).first()
        if not self.numero_orden:
            self.numero_orden = CorrelativoServicio.siguiente('ORDEN', 'OS')
        super().save(*args, **kwargs)
        if estado_anterior != self.estado:
            HistorialOrdenServicio.objects.create(
                orden_servicio=self,
                estado_anterior=estado_anterior or '',
                estado_nuevo=self.estado,
                observacion=observacion_historial,
                usuario=usuario_historial,
            )


class AnticipoOrdenServicio(models.Model):
    orden_servicio = models.ForeignKey(OrdenServicio, on_delete=models.CASCADE, related_name='anticipos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(default=timezone.now)
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='anticipos_servicio_registrados')

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.orden_servicio.numero_orden} - Q{self.monto}'

    def clean(self):
        errors = {}
        if self.monto is not None and self.monto <= 0:
            errors['monto'] = 'El anticipo debe ser mayor a cero.'
        if self.orden_servicio_id and self.orden_servicio.estado != OrdenServicio.Estado.APROBADO_REPARACION:
            errors[NON_FIELD_ERRORS] = 'Solo se pueden registrar anticipos cuando la reparación está aprobada.'
        if self.orden_servicio_id and self.monto and self.monto > 0:
            anticipos_previos = self.orden_servicio.anticipos.exclude(pk=self.pk).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            total_aprobado = self.orden_servicio.total_aprobado
            if total_aprobado > 0 and anticipos_previos + self.monto > total_aprobado:
                errors['monto'] = 'El total de anticipos no puede superar el total aprobado.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class HistorialOrdenServicio(models.Model):
    orden_servicio = models.ForeignKey(OrdenServicio, on_delete=models.CASCADE, related_name='historial_estados')
    estado_anterior = models.CharField(max_length=30, blank=True)
    estado_nuevo = models.CharField(max_length=30, choices=OrdenServicio.Estado.choices)
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']


class SeguimientoOrdenServicio(models.Model):
    class Tipo(models.TextChoices):
        DIAGNOSTICO = 'DIAGNOSTICO', 'Diagnóstico'
        PRUEBA = 'PRUEBA', 'Prueba realizada'
        OBSERVACION = 'OBSERVACION', 'Observación técnica'
        REPUESTO = 'REPUESTO', 'Repuesto pendiente'
        AVANCE = 'AVANCE', 'Avance'
        NOTA_INTERNA = 'NOTA_INTERNA', 'Nota interna'
        CONTACTO_CLIENTE = 'CONTACTO_CLIENTE', 'Contacto con cliente'

    orden_servicio = models.ForeignKey(OrdenServicio, on_delete=models.CASCADE, related_name='seguimientos')
    tipo_seguimiento = models.CharField(max_length=25, choices=Tipo.choices)
    descripcion = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-id']


class CotizacionServicio(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador'
        ENVIADA = 'ENVIADA', 'Enviada'
        APROBADA = 'APROBADA', 'Aprobada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    orden_servicio = models.ForeignKey(OrdenServicio, on_delete=models.CASCADE, related_name='cotizaciones_servicio')
    numero_cotizacion = models.CharField(max_length=20, unique=True, blank=True)
    fecha = models.DateField(default=timezone.localdate)
    vigencia = models.PositiveIntegerField(default=15, help_text='Días de vigencia')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    observaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.BORRADOR)
    usuario_creacion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.numero_cotizacion

    @property
    def saldo_despues_anticipo(self):
        return max(
            (self.total or Decimal('0.00')) - self.orden_servicio.total_anticipos,
            Decimal('0.00'),
        )

    def clean(self):
        errors = {}
        if self.vigencia < 1:
            errors['vigencia'] = 'La vigencia debe ser mayor a cero.'
        if self.descuento < 0:
            errors['descuento'] = 'El descuento no puede ser negativo.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            self.numero_cotizacion = CorrelativoServicio.siguiente('COTIZACION', 'CST')
        super().save(*args, **kwargs)

    def actualizar_totales(self):
        subtotal = self.detalles.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        self.subtotal = subtotal
        self.total = max(subtotal - (self.descuento or Decimal('0.00')), Decimal('0.00'))
        type(self).objects.filter(pk=self.pk).update(subtotal=self.subtotal, total=self.total)


class DetalleCotizacionServicio(models.Model):
    class TipoItem(models.TextChoices):
        REPUESTO = 'REPUESTO', 'Repuesto'
        MANO_OBRA = 'MANO_OBRA', 'Mano de obra'
        SERVICIO = 'SERVICIO', 'Servicio'

    cotizacion = models.ForeignKey(CotizacionServicio, on_delete=models.CASCADE, related_name='detalles')
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tipo_item = models.CharField(max_length=15, choices=TipoItem.choices, default=TipoItem.SERVICIO)

    class Meta:
        ordering = ['id']

    def clean(self):
        errors = {}
        if self.cantidad <= 0:
            errors['cantidad'] = 'La cantidad debe ser mayor a cero.'
        if self.precio_unitario < 0:
            errors['precio_unitario'] = 'El precio no puede ser negativo.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.subtotal = (self.cantidad or Decimal('0.00')) * (self.precio_unitario or Decimal('0.00'))
        super().save(*args, **kwargs)
        self.cotizacion.actualizar_totales()

    def delete(self, *args, **kwargs):
        cotizacion = self.cotizacion
        super().delete(*args, **kwargs)
        cotizacion.actualizar_totales()
