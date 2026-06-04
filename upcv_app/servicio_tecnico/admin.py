from django.contrib import admin

from .models import AnticipoOrdenServicio, CotizacionServicio, DetalleCotizacionServicio, HistorialOrdenServicio, OrdenServicio, SeguimientoOrdenServicio


class SeguimientoInline(admin.TabularInline):
    model = SeguimientoOrdenServicio
    extra = 0


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'cliente', 'tipo_equipo', 'estado', 'prioridad', 'total_anticipos', 'tecnico_asignado', 'fecha_recepcion')
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


@admin.register(AnticipoOrdenServicio)
class AnticipoOrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('orden_servicio', 'monto', 'fecha', 'usuario')
    list_filter = ('fecha',)
    search_fields = ('orden_servicio__numero_orden', 'orden_servicio__cliente__nombre', 'observacion')
    readonly_fields = ('usuario',)

    def save_model(self, request, obj, form, change):
        if not obj.usuario_id:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)
