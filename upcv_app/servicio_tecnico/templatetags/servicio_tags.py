from django import template

register = template.Library()


@register.filter
def estado_badge(estado):
    return {
        'RECIBIDO': 'info', 'EN_DIAGNOSTICO': 'primary', 'PENDIENTE_COTIZACION': 'warning',
        'COTIZADO': 'secondary', 'APROBADO_REPARACION': 'success', 'EN_REPARACION': 'primary',
        'PENDIENTE_REPUESTO': 'warning', 'REPARADO': 'success', 'LISTO_PARA_ENTREGAR': 'success',
        'ENTREGADO': 'dark', 'NO_REPARADO': 'danger', 'CANCELADO': 'danger', 'BORRADOR': 'secondary',
        'ENVIADA': 'info', 'APROBADA': 'success', 'RECHAZADA': 'danger',
    }.get(estado, 'secondary')
