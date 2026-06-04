from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def migrar_anticipos_existentes(apps, schema_editor):
    OrdenServicio = apps.get_model('servicio_tecnico', 'OrdenServicio')
    AnticipoOrdenServicio = apps.get_model('servicio_tecnico', 'AnticipoOrdenServicio')
    for orden in OrdenServicio.objects.filter(anticipo__gt=Decimal('0.00')).iterator():
        AnticipoOrdenServicio.objects.create(
            orden_servicio=orden,
            monto=orden.anticipo,
            fecha=orden.fecha_actualizacion,
            observacion='Anticipo migrado desde la orden de servicio.',
            usuario=orden.usuario_creacion,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('servicio_tecnico', '0003_ordenservicio_anticipo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnticipoOrdenServicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('fecha', models.DateTimeField(default=django.utils.timezone.now)),
                ('observacion', models.TextField(blank=True)),
                ('orden_servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='anticipos', to='servicio_tecnico.ordenservicio')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='anticipos_servicio_registrados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-fecha', '-id']},
        ),
        migrations.RunPython(migrar_anticipos_existentes, migrations.RunPython.noop),
        migrations.RemoveField(model_name='ordenservicio', name='anticipo'),
    ]
