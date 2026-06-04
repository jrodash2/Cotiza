import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def migrar_anticipos_a_pagos(apps, schema_editor):
    Anticipo = apps.get_model('servicio_tecnico', 'AnticipoOrdenServicio')
    Pago = apps.get_model('servicio_tecnico', 'PagoOrdenServicio')
    for anticipo in Anticipo.objects.all().iterator():
        Pago.objects.create(
            orden_servicio=anticipo.orden_servicio,
            numero_recibo=f'REC-MIG-{anticipo.pk:08d}',
            fecha=anticipo.fecha,
            monto=anticipo.monto,
            tipo_pago='ANTICIPO',
            metodo_pago='OTRO',
            observacion=anticipo.observacion or 'Anticipo migrado al historial de pagos.',
            usuario_registro=anticipo.usuario,
            activo=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('servicio_tecnico', '0004_anticipoordenservicio_remove_ordenservicio_anticipo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='PagoOrdenServicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_recibo', models.CharField(blank=True, max_length=20, unique=True)),
                ('fecha', models.DateTimeField(default=django.utils.timezone.now)),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('tipo_pago', models.CharField(choices=[('ANTICIPO', 'Anticipo'), ('ABONO', 'Abono'), ('PAGO_FINAL', 'Pago final'), ('AJUSTE', 'Ajuste')], default='ABONO', max_length=15)),
                ('metodo_pago', models.CharField(choices=[('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('DEPOSITO', 'Depósito'), ('TARJETA', 'Tarjeta'), ('OTRO', 'Otro')], default='EFECTIVO', max_length=20)),
                ('referencia', models.CharField(blank=True, max_length=150)),
                ('observacion', models.TextField(blank=True)),
                ('activo', models.BooleanField(default=True)),
                ('fecha_anulacion', models.DateTimeField(blank=True, null=True)),
                ('orden_servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagos', to='servicio_tecnico.ordenservicio')),
                ('usuario_anulacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='pagos_servicio_anulados', to=settings.AUTH_USER_MODEL)),
                ('usuario_registro', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagos_servicio_registrados', to=settings.AUTH_USER_MODEL)),
            ], options={'ordering': ['-fecha', '-id']},
        ),
        migrations.RunPython(migrar_anticipos_a_pagos, migrations.RunPython.noop),
        migrations.DeleteModel(name='AnticipoOrdenServicio'),
    ]
