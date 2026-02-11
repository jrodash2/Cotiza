from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView

from .forms import VentaForm, VentaItemFormSet
from .models import (
    Articulo,
    DetalleVentaArticulo,
    DetalleVentaServicio,
    Kardex,
    Servicio,
    Venta,
)


@login_required
def lista_ventas(request):
    ventas = (
        Venta.objects.select_related('cliente', 'usuario', 'origen_cotizacion')
        .prefetch_related('detalles_articulos__articulo', 'detalles_servicios__servicio')
        .all()
    )
    return render(request, 'ventas/lista.html', {'ventas': ventas})


class VentaCreateView(LoginRequiredMixin, CreateView):
    model = Venta
    form_class = VentaForm
    template_name = 'ventas/venta_form.html'

    def get(self, request, *args, **kwargs):
        self.object = None
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.object = None
        context = super().get_context_data(**kwargs)
        if 'formset' not in context:
            if self.request.POST:
                context['formset'] = VentaItemFormSet(self.request.POST, prefix='items')
            else:
                context['formset'] = VentaItemFormSet(prefix='items')
        context['venta'] = self.object
        context['fecha_emision'] = timezone.now()
        context['search_url'] = 'ventas:buscar_items'
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        formset = VentaItemFormSet(request.POST, prefix='items')

        if form.is_valid() and formset.is_valid():
            return self.forms_valid(form, formset)
        return self.forms_invalid(form, formset)

    def forms_invalid(self, form, formset):
        messages.error(self.request, 'Revisa los errores en el formulario.')
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def forms_valid(self, form, formset):
        with transaction.atomic():
            venta = form.save(commit=False)
            venta.usuario = self.request.user
            venta.estado = venta.estado or Venta.ESTADO_BORRADOR
            venta.save()

            errores = []
            for idx, item_form in enumerate(formset.forms, start=1):
                if not item_form.cleaned_data or item_form.cleaned_data.get('DELETE'):
                    continue

                item_type = item_form.cleaned_data.get('item_type')
                item_id = item_form.cleaned_data.get('item_id')
                cantidad = item_form.cleaned_data.get('cantidad')
                precio_unitario = item_form.cleaned_data.get('precio_unitario')

                if not item_type or not item_id:
                    errores.append(f'Línea {idx}: ítem inválido.')
                    continue

                if item_type == 'articulo':
                    articulo = Articulo.objects.select_for_update().filter(pk=item_id, activo=True).first()
                    if not articulo:
                        errores.append(f'Línea {idx}: artículo inexistente.')
                        continue
                    if cantidad > articulo.stock:
                        errores.append(
                            f'Línea {idx}: stock insuficiente para {articulo.nombre}. Disponible: {articulo.stock}.'
                        )
                        continue
                    DetalleVentaArticulo.objects.create(
                        venta=venta,
                        articulo=articulo,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                    )
                elif item_type == 'servicio':
                    servicio = Servicio.objects.filter(pk=item_id, activo=True).first()
                    if not servicio:
                        errores.append(f'Línea {idx}: servicio inexistente.')
                        continue
                    DetalleVentaServicio.objects.create(
                        venta=venta,
                        servicio=servicio,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                    )
                else:
                    errores.append(f'Línea {idx}: tipo de ítem inválido.')

            if errores:
                transaction.set_rollback(True)
                for error in errores:
                    messages.error(self.request, error)
                return self.forms_invalid(form, formset)

            venta.actualizar_total()

        messages.success(self.request, 'Venta creada correctamente.')
        return redirect('ventas:detalle_venta', id=venta.pk)


crear_venta = login_required(VentaCreateView.as_view())


@login_required
def detalle_venta(request, id):
    venta = get_object_or_404(
        Venta.objects.select_related('cliente', 'usuario', 'origen_cotizacion').prefetch_related(
            'detalles_articulos__articulo',
            'detalles_servicios__servicio',
        ),
        id=id,
    )
    return render(request, 'ventas/detalle.html', {'venta': venta})


@login_required
@require_POST
@transaction.atomic
def confirmar_venta(request, id):
    venta = get_object_or_404(
        Venta.objects.select_for_update().prefetch_related('detalles_articulos__articulo', 'detalles_servicios'),
        id=id,
    )

    if venta.estado != Venta.ESTADO_BORRADOR:
        messages.error(request, 'Solo se pueden confirmar ventas en borrador.')
        return redirect('ventas:detalle_venta', id=venta.id)

    detalles_articulos = list(venta.detalles_articulos.select_related('articulo'))
    detalles_servicios = list(venta.detalles_servicios.select_related('servicio'))
    if not detalles_articulos and not detalles_servicios:
        messages.error(request, 'No puedes confirmar una venta sin detalles.')
        return redirect('ventas:detalle_venta', id=venta.id)

    for detalle in detalles_articulos:
        articulo = Articulo.objects.select_for_update().get(id=detalle.articulo_id)
        if detalle.cantidad > articulo.stock:
            messages.error(
                request,
                f'Stock insuficiente para {articulo.nombre}. Disponible: {articulo.stock}.',
            )
            return redirect('ventas:detalle_venta', id=venta.id)

    for detalle in detalles_articulos:
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
    venta = get_object_or_404(
        Venta.objects.select_for_update().prefetch_related('detalles_articulos__articulo', 'detalles_servicios'),
        id=id,
    )

    if venta.estado == Venta.ESTADO_ANULADA:
        messages.warning(request, 'La venta ya fue anulada previamente.')
        return redirect('ventas:detalle_venta', id=venta.id)

    if venta.estado == Venta.ESTADO_CONFIRMADA:
        for detalle in venta.detalles_articulos.select_related('articulo'):
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
def buscar_items(request):
    term = request.GET.get('q', '').strip()

    articulos = Articulo.objects.filter(activo=True)
    servicios = Servicio.objects.filter(activo=True)
    if term:
        articulos = articulos.filter(Q(nombre__icontains=term) | Q(codigo__icontains=term))
        servicios = servicios.filter(Q(nombre__icontains=term) | Q(codigo__icontains=term))

    data_articulos = [
        {
            'type': 'articulo',
            'id': articulo.id,
            'codigo': articulo.codigo,
            'nombre': articulo.nombre,
            'stock': float(articulo.stock),
            'precio': float(articulo.precio_venta),
        }
        for articulo in articulos.order_by('nombre')[:20]
    ]
    data_servicios = [
        {
            'type': 'servicio',
            'id': servicio.id,
            'codigo': servicio.codigo,
            'nombre': servicio.nombre,
            'precio': float(servicio.precio_venta),
        }
        for servicio in servicios.order_by('nombre')[:20]
    ]
    return JsonResponse({'results': data_articulos + data_servicios})


@login_required
@require_GET
def item_detail(request, item_type, item_id):
    item_type = item_type.strip().lower()
    if item_type == 'articulo':
        articulo = get_object_or_404(Articulo, pk=item_id, activo=True)
        data = {
            'type': 'articulo',
            'id': articulo.id,
            'codigo': articulo.codigo,
            'nombre': articulo.nombre,
            'stock': float(articulo.stock),
            'precio': float(articulo.precio_venta),
            'descripcion': articulo.descripcion,
        }
    elif item_type == 'servicio':
        servicio = get_object_or_404(Servicio, pk=item_id, activo=True)
        data = {
            'type': 'servicio',
            'id': servicio.id,
            'codigo': servicio.codigo,
            'nombre': servicio.nombre,
            'precio': float(servicio.precio_venta),
            'descripcion': servicio.descripcion,
        }
    else:
        return JsonResponse({'error': 'Tipo de ítem inválido.'}, status=400)

    return JsonResponse(data)
