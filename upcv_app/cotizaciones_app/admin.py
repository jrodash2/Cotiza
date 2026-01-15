from django.contrib import admin

from .models import Cliente, ProductoServicio, Cotizacion, CotizacionItem, CotizacionCorrelativo


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email', 'nit', 'municipio', 'departamento')
    search_fields = ('nombre', 'telefono', 'email', 'nit')


@admin.register(ProductoServicio)
class ProductoServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'precio_costo', 'precio_venta', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre', 'descripcion')


class CotizacionItemInline(admin.TabularInline):
    model = CotizacionItem
    extra = 0


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('correlativo', 'fecha_emision', 'cliente', 'estado', 'subtotal_venta', 'ganancia_total')
    list_filter = ('estado',)
    search_fields = ('correlativo', 'cliente__nombre')
    inlines = [CotizacionItemInline]


@admin.register(CotizacionCorrelativo)
class CotizacionCorrelativoAdmin(admin.ModelAdmin):
    list_display = ('id', 'last_number')
