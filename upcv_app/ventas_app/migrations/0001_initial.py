from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cotizaciones_app', '0002_venta_pagoventa'),
    ]

    operations = [
        migrations.CreateModel(
            name='Articulo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=40, unique=True)),
                ('nombre', models.CharField(max_length=200)),
                ('descripcion', models.TextField(blank=True)),
                ('stock', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('precio_venta', models.DecimalField(decimal_places=2, max_digits=12)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={'ordering': ['nombre']},
        ),
        migrations.CreateModel(
            name='VentaCorrelativo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_number', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Kardex',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('ENTRADA', 'Entrada'), ('SALIDA', 'Salida')], max_length=10)),
                ('cantidad', models.DecimalField(decimal_places=2, max_digits=10)),
                ('referencia', models.CharField(max_length=120)),
                ('observacion', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('articulo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos_kardex', to='ventas_app.articulo')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-creado_en', '-id']},
        ),
        migrations.CreateModel(
            name='Venta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('correlativo', models.CharField(blank=True, max_length=20, unique=True)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('estado', models.CharField(choices=[('BORRADOR', 'Borrador'), ('CONFIRMADA', 'Confirmada'), ('ANULADA', 'Anulada')], default='BORRADOR', max_length=20)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('cliente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ventas_directas', to='cotizaciones_app.cliente')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ventas_creadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-fecha', '-id']},
        ),
        migrations.CreateModel(
            name='DetalleVenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=2, max_digits=10)),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=12)),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('articulo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ventas_app.articulo')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='ventas_app.venta')),
            ],
            options={'ordering': ['id']},
        ),
    ]
