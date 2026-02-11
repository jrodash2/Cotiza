import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import VentaForm
from .models import Articulo, DetalleVenta, Kardex, Venta


@login_required
def lista_ventas(request):
    ventas = (
        Venta.objects.select_related('cliente', 'usuario')
        .prefetch_related('detalles__articulo')
        .all()
    )
    return render(request, 'ventas/lista.html', {'ventas': ventas})


@login_required
@transaction.atomic
def crear_venta(request):
    if request.method == 'POST':
        form = VentaForm(request.POST)
        detalles_json = request.POST.get('detalles_json', '[]')

        if not form.is_valid():
            messages.error(request, 'Verifica los datos de cabecera de la venta.')
        else:
            try:
                detalles_payload = json.loads(detalles_json)
            except json.JSONDecodeError:
                detalles_payload = []

            if not detalles_payload:
                messages.error(request, 'Debes agregar al menos un artículo para crear la venta.')
                return render(
                    request,
                    'ventas/crear.html',
                    {'form': form, 'articulos': Articulo.objects.filter(activo=True).order_by('nombre')},
                )

            venta = form.save(commit=False)
            venta.usuario = request.user
            venta.estado = Venta.ESTADO_BORRADOR
            venta.save()

            errores = []
            for idx, item in enumerate(detalles_payload, start=1):
                try:
                    articulo_id = int(item.get('articulo_id'))
                    cantidad = Decimal(str(item.get('cantidad')))
                    precio = Decimal(str(item.get('precio_unitario')))
                except (TypeError, ValueError, InvalidOperation):
                    errores.append(f'Línea {idx}: datos inválidos.')
                    continue

                articulo = Articulo.objects.filter(pk=articulo_id, activo=True).first()
                if not articulo:
                    errores.append(f'Línea {idx}: artículo inexistente.')
                    continue
                if cantidad <= 0:
                    errores.append(f'Línea {idx}: cantidad inválida.')
                    continue
                if precio < 0:
                    errores.append(f'Línea {idx}: precio inválido.')
                    continue
                if cantidad > articulo.stock:
                    errores.append(
                        f'Línea {idx}: stock insuficiente para {articulo.nombre}. Disponible: {articulo.stock}.'
                    )
                    continue

                detalle = DetalleVenta(
                    venta=venta,
                    articulo=articulo,
                    cantidad=cantidad,
                    precio_unitario=precio,
                )
                detalle.full_clean()
                detalle.save()

            if errores:
                transaction.set_rollback(True)
                for error in errores:
                    messages.error(request, error)
                return render(
                    request,
                    'ventas/crear.html',
                    {'form': form, 'articulos': Articulo.objects.filter(activo=True).order_by('nombre')},
                )

            venta.actualizar_total()
            messages.success(request, f'Venta {venta.correlativo} creada en borrador correctamente.')
            return redirect('ventas:detalle_venta', id=venta.id)
    else:
        form = VentaForm()

    articulos = Articulo.objects.filter(activo=True).order_by('nombre')
    return render(request, 'ventas/crear.html', {'form': form, 'articulos': articulos})


@login_required
def detalle_venta(request, id):
    venta = get_object_or_404(
        Venta.objects.select_related('cliente', 'usuario').prefetch_related('detalles__articulo'),
        id=id,
    )
    return render(request, 'ventas/detalle.html', {'venta': venta})


@login_required
@require_POST
@transaction.atomic
def confirmar_venta(request, id):
    venta = get_object_or_404(Venta.objects.select_for_update().prefetch_related('detalles__articulo'), id=id)

    if venta.estado != Venta.ESTADO_BORRADOR:
        messages.error(request, 'Solo se pueden confirmar ventas en borrador.')
        return redirect('ventas:detalle_venta', id=venta.id)

    detalles = list(venta.detalles.select_related('articulo'))
    if not detalles:
        messages.error(request, 'No puedes confirmar una venta sin detalles.')
        return redirect('ventas:detalle_venta', id=venta.id)

    for detalle in detalles:
        articulo = Articulo.objects.select_for_update().get(id=detalle.articulo_id)
        if detalle.cantidad > articulo.stock:
            messages.error(
                request,
                f'Stock insuficiente para {articulo.nombre}. Disponible: {articulo.stock}.',
            )
            return redirect('ventas:detalle_venta', id=venta.id)

    for detalle in detalles:
        Articulo.objects.filter(id=detalle.articulo_id).update(stock=F('stock') - detalle.cantidad)
        Kardex.objects.create(
            articulo_id=detalle.articulo_id,
            tipo=Kardex.TIPO_SALIDA,
            cantidad=detalle.cantidad,
            referencia=venta.correlativo,
            observacion='Salida por confirmación de venta',
            usuario=request.user,
        )

    venta.estado = Venta.ESTADO_CONFIRMADA
    venta.save(update_fields=['estado', 'actualizado_en'])
    messages.success(request, f'Venta {venta.correlativo} confirmada y stock actualizado.')
    return redirect('ventas:detalle_venta', id=venta.id)


@login_required
@require_POST
@transaction.atomic
def anular_venta(request, id):
    venta = get_object_or_404(Venta.objects.select_for_update().prefetch_related('detalles__articulo'), id=id)

    if venta.estado == Venta.ESTADO_ANULADA:
        messages.warning(request, 'La venta ya fue anulada previamente.')
        return redirect('ventas:detalle_venta', id=venta.id)

    if venta.estado == Venta.ESTADO_CONFIRMADA:
        for detalle in venta.detalles.select_related('articulo'):
            Articulo.objects.filter(id=detalle.articulo_id).update(stock=F('stock') + detalle.cantidad)
            Kardex.objects.create(
                articulo_id=detalle.articulo_id,
                tipo=Kardex.TIPO_ENTRADA,
                cantidad=detalle.cantidad,
                referencia=venta.correlativo,
                observacion='Entrada por anulación de venta confirmada',
                usuario=request.user,
            )

    venta.estado = Venta.ESTADO_ANULADA
    venta.save(update_fields=['estado', 'actualizado_en'])
    messages.success(request, f'Venta {venta.correlativo} anulada correctamente.')
    return redirect('ventas:detalle_venta', id=venta.id)


@login_required
@require_GET
def buscar_articulos(request):
    term = request.GET.get('q', '').strip()
    articulos = Articulo.objects.filter(activo=True)
    if term:
        articulos = articulos.filter(Q(nombre__icontains=term) | Q(codigo__icontains=term))

    data = [
        {
            'id': articulo.id,
            'codigo': articulo.codigo,
            'nombre': articulo.nombre,
            'stock': float(articulo.stock),
            'precio_venta': float(articulo.precio_venta),
        }
        for articulo in articulos.order_by('nombre')[:20]
    ]
    return JsonResponse({'results': data})
