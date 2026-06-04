# Módulo de servicio técnico

El módulo reutiliza `cotizaciones_app.Cliente` y `almacen_app.Institucion`. Los correlativos anuales se generan en `CorrelativoServicio` dentro de una transacción. Todo cambio de estado realizado mediante `OrdenServicio.save()` crea automáticamente un registro de historial; las vistas pasan el usuario y la observación responsable.

## Roles

- `Recepcion` o `Almacen`: recepción, cotización y entrega.
- `Tecnico` o `Técnico`: seguimiento y actualización técnica.
- `Administrador` y superusuarios: acceso completo.

## Puesta en marcha

1. Ejecutar `python manage.py migrate`.
2. Crear/asignar los grupos anteriores desde administración.
3. Acceder a `/servicio-tecnico/`.

## Pagos parciales y saldo

Los movimientos se registran en `PagoOrdenServicio` con recibo, tipo, método, referencia, fecha, usuario y estado activo. Se permiten pagos desde `APROBADO_REPARACION` y durante reparación, repuesto pendiente, reparación terminada, listo para entrega y entregado. Los pagos anulados conservan fecha y usuario de anulación, pero no suman. Cada pago genera un correlativo y un recibo PDF individual.

La base de cobro es `costo_final` cuando es mayor que cero; de lo contrario se utiliza la cotización aprobada. El sistema calcula `total_pagado`, `anticipo_total`, `saldo_pendiente`, `esta_pagada` y `estado_pago`, bloqueando sobrepagos y pagos sin una base de cobro.

## Detalle de cotización

El formulario usa un inline formset con `management_form` y `DELETE`. La interfaz permite agregar y eliminar líneas dinámicamente; las eliminaciones se procesan en backend y cada alta, cambio o baja recalcula los totales.
