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

## Anticipos y saldo

Los anticipos se registran en `AnticipoOrdenServicio`, únicamente cuando la orden está en `APROBADO_REPARACION`. Esto permite múltiples pagos, usuario/fecha/observación por movimiento y conserva trazabilidad. El saldo usa el total de la cotización aprobada o, si no existe, el costo final.

## Detalle de cotización

El formulario usa un inline formset con `management_form` y `DELETE`. La interfaz permite agregar y eliminar líneas dinámicamente; las eliminaciones se procesan en backend y cada alta, cambio o baja recalcula los totales.
