from decimal import Decimal

from django.db import migrations, models
from django.db.models import Sum, Q


def asignar_cotizaciones_vigentes(apps, schema_editor):
    CotizacionServicio = apps.get_model('servicio_tecnico', 'CotizacionServicio')
    PagoOrdenServicio = apps.get_model('servicio_tecnico', 'PagoOrdenServicio')
    OrdenServicio = apps.get_model('servicio_tecnico', 'OrdenServicio')

    for orden in OrdenServicio.objects.all().only('id'):
        aprobadas = CotizacionServicio.objects.filter(
            orden_servicio_id=orden.id,
            estado='APROBADA',
        )
        if not aprobadas.exists():
            continue

        total_pagado = PagoOrdenServicio.objects.filter(
            orden_servicio_id=orden.id,
            activo=True,
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        if total_pagado > 0:
            vigente = aprobadas.filter(total__gte=total_pagado).order_by('total', '-fecha', '-id').first()
        else:
            vigente = aprobadas.order_by('-fecha', '-id').first()

        if not vigente:
            vigente = aprobadas.order_by('-fecha', '-id').first()
        CotizacionServicio.objects.filter(pk=vigente.pk).update(es_vigente=True)


def limpiar_cotizaciones_vigentes(apps, schema_editor):
    CotizacionServicio = apps.get_model('servicio_tecnico', 'CotizacionServicio')
    CotizacionServicio.objects.update(es_vigente=False)


class Migration(migrations.Migration):

    dependencies = [
        ('servicio_tecnico', '0005_pagoordenservicio_remove_anticipoordenservicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='cotizacionservicio',
            name='es_vigente',
            field=models.BooleanField(default=False, help_text='Cotización vigente usada como base de cobro de la orden.'),
        ),
        migrations.RunPython(asignar_cotizaciones_vigentes, limpiar_cotizaciones_vigentes),
        migrations.AddConstraint(
            model_name='cotizacionservicio',
            constraint=models.UniqueConstraint(
                fields=('orden_servicio',),
                condition=Q(es_vigente=True),
                name='servicio_cotizacion_vigente_unica_por_orden',
            ),
        ),
    ]
