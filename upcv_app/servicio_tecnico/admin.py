from django.contrib import admin

from .models import PagoOrdenServicio, CotizacionServicio, DetalleCotizacionServicio, HistorialOrdenServicio, OrdenServicio, SeguimientoOrdenServicio


class SeguimientoInline(admin.TabularInline):
    model = SeguimientoOrdenServicio
    extra = 0


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'cliente', 'tipo_equipo', 'estado', 'prioridad', 'total_pagado', 'tecnico_asignado', 'fecha_recepcion')
    list_filter = ('estado', 'prioridad', 'tipo_equipo', 'activo')
    search_fields = ('numero_orden', 'cliente__nombre', 'numero_serie', 'marca', 'modelo')
    readonly_fields = ('numero_orden', 'fecha_recepcion', 'fecha_actualizacion')
    inlines = [SeguimientoInline]


@admin.register(HistorialOrdenServicio)
class HistorialOrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('orden_servicio', 'estado_anterior', 'estado_nuevo', 'usuario', 'fecha')
    readonly_fields = ('orden_servicio', 'estado_anterior', 'estado_nuevo', 'observacion', 'usuario', 'fecha')


class DetalleCotizacionInline(admin.TabularInline):
    model = DetalleCotizacionServicio
    extra = 0


@admin.register(CotizacionServicio)
class CotizacionServicioAdmin(admin.ModelAdmin):
    list_display = ('numero_cotizacion', 'orden_servicio', 'fecha', 'estado', 'total')
    list_filter = ('estado', 'fecha')
    search_fields = ('numero_cotizacion', 'orden_servicio__numero_orden', 'orden_servicio__cliente__nombre')
    readonly_fields = ('numero_cotizacion', 'subtotal', 'total', 'fecha_actualizacion')
    inlines = [DetalleCotizacionInline]


@admin.register(PagoOrdenServicio)
class PagoOrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('numero_recibo', 'orden_servicio', 'tipo_pago', 'metodo_pago', 'monto', 'fecha', 'activo')
    list_filter = ('activo', 'tipo_pago', 'metodo_pago', 'fecha')
    search_fields = ('orden_servicio__numero_orden', 'orden_servicio__cliente__nombre', 'observacion')
    readonly_fields = ('numero_recibo', 'usuario_registro', 'activo', 'fecha_anulacion', 'usuario_anulacion')

    def save_model(self, request, obj, form, change):
        if not obj.usuario_registro_id:
            obj.usuario_registro = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False
