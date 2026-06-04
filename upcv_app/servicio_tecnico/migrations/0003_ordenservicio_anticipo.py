from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('servicio_tecnico', '0002_crear_roles_servicio')]

    operations = [
        migrations.AddField(
            model_name='ordenservicio',
            name='anticipo',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=12,
                verbose_name='Anticipo recibido',
            ),
        ),
    ]
