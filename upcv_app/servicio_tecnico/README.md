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

La orden permite registrar un anticipo no negativo. Cuando existe un costo final, el anticipo no puede superarlo. `saldo_pendiente` devuelve la diferencia entre costo final y anticipo, con límite mínimo de cero. El anticipo se incluye en la constancia de recepción y en el resumen económico de la orden/cotización.
