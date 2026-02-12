from django.contrib import admin

from .models import (
    Articulo,
    DetalleVenta,
    DetalleVentaArticulo,
    DetalleVentaServicio,
    Kardex,
    Servicio,
    Venta,
)


@admin.register(Articulo)
class ArticuloAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'stock', 'precio_venta', 'activo')
    search_fields = ('codigo', 'nombre')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'precio_venta', 'activo')
    search_fields = ('codigo', 'nombre')


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0


class DetalleVentaArticuloInline(admin.TabularInline):
    model = DetalleVentaArticulo
    extra = 0


class DetalleVentaServicioInline(admin.TabularInline):
    model = DetalleVentaServicio
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('correlativo', 'fecha', 'cliente', 'total', 'estado', 'usuario', 'origen_cotizacion')
    list_filter = ('estado',)
    search_fields = ('correlativo', 'cliente__nombre')
    inlines = [DetalleVentaArticuloInline, DetalleVentaServicioInline, DetalleVentaInline]


@admin.register(Kardex)
class KardexAdmin(admin.ModelAdmin):
    list_display = ('articulo', 'tipo', 'cantidad', 'referencia', 'usuario', 'creado_en')
    list_filter = ('tipo',)
