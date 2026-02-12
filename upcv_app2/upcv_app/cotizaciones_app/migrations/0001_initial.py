from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200)),
                ('contacto', models.CharField(blank=True, max_length=200)),
                ('telefono', models.CharField(blank=True, max_length=50)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('direccion', models.CharField(blank=True, max_length=255)),
                ('nit', models.CharField(blank=True, max_length=50)),
                ('municipio', models.CharField(blank=True, max_length=100)),
                ('departamento', models.CharField(blank=True, max_length=100)),
                ('notas', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Cotizacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('correlativo', models.CharField(blank=True, max_length=5, unique=True)),
                ('fecha_emision', models.DateField(default=django.utils.timezone.now)),
                ('titulo', models.CharField(blank=True, max_length=255)),
                ('validez_dias', models.PositiveIntegerField(default=15)),
                ('observaciones', models.TextField(blank=True)),
                ('garantia_texto', models.CharField(default='GARANTIA DE 6 MESES EN EQUIPOS E INSTALACIÓN', max_length=255)),
                ('estado', models.CharField(choices=[('BORRADOR', 'Borrador'), ('EMITIDA', 'Emitida'), ('ANULADA', 'Anulada')], default='BORRADOR', max_length=20)),
                ('subtotal_venta', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('subtotal_costo', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('ganancia_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cotizaciones', to='cotizaciones_app.cliente')),
            ],
            options={
                'ordering': ['-fecha_emision', '-id'],
            },
        ),
        migrations.CreateModel(
            name='CotizacionCorrelativo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_number', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='ProductoServicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('PRODUCTO', 'Producto'), ('SERVICIO', 'Servicio')], max_length=20)),
                ('nombre', models.CharField(max_length=200)),
                ('descripcion', models.TextField(blank=True)),
                ('unidad', models.CharField(blank=True, max_length=50)),
                ('precio_costo', models.DecimalField(decimal_places=2, max_digits=12)),
                ('precio_venta', models.DecimalField(decimal_places=2, max_digits=12)),
                ('activo', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='CotizacionItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion_editable', models.TextField(blank=True)),
                ('cantidad', models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=10)),
                ('precio_venta_unitario', models.DecimalField(decimal_places=2, max_digits=12)),
                ('precio_costo_unitario', models.DecimalField(decimal_places=2, max_digits=12)),
                ('total_linea_venta', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('total_linea_costo', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('ganancia_linea', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cotizacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='cotizaciones_app.cotizacion')),
                ('producto_servicio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='cotizaciones_app.productoservicio')),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
