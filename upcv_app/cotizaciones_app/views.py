from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from almacen_app.models import Institucion
from .forms import (
    ClienteForm,
    ProductoServicioForm,
    CotizacionForm,
    CotizacionItemFormSet,
    PagoVentaForm,
)
from .models import Cliente, ProductoServicio, Cotizacion, Venta, PagoVenta


class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'cotizaciones_app/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by('nombre')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q)
                | Q(telefono__icontains=q)
                | Q(email__icontains=q)
                | Q(nit__icontains=q)
            )
        return queryset


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cotizaciones_app/cliente_form.html'
    success_url = reverse_lazy('cotizaciones:cliente_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente creado correctamente.')
        return super().form_valid(form)


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cotizaciones_app/cliente_form.html'
    success_url = reverse_lazy('cotizaciones:cliente_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado correctamente.')
        return super().form_valid(form)


class ProductoServicioListView(LoginRequiredMixin, ListView):
    model = ProductoServicio
    template_name = 'cotizaciones_app/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by('nombre')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
        return queryset


class ProductoServicioCreateView(LoginRequiredMixin, CreateView):
    model = ProductoServicio
    form_class = ProductoServicioForm
    template_name = 'cotizaciones_app/producto_form.html'
    success_url = reverse_lazy('cotizaciones:producto_list')

    def form_valid(self, form):
        messages.success(self.request, 'Producto/servicio creado correctamente.')
        return super().form_valid(form)


class ProductoServicioUpdateView(LoginRequiredMixin, UpdateView):
    model = ProductoServicio
    form_class = ProductoServicioForm
    template_name = 'cotizaciones_app/producto_form.html'
    success_url = reverse_lazy('cotizaciones:producto_list')

    def form_valid(self, form):
        messages.success(self.request, 'Producto/servicio actualizado correctamente.')
        return super().form_valid(form)


class CotizacionListView(LoginRequiredMixin, ListView):
    model = Cotizacion
    template_name = 'cotizaciones_app/cotizacion_list.html'
    context_object_name = 'cotizaciones'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente')
        cliente_id = self.request.GET.get('cliente')
        q_cliente = self.request.GET.get('q_cliente')
        estado = self.request.GET.get('estado')
        fecha_inicio = parse_date(self.request.GET.get('fecha_inicio', ''))
        fecha_fin = parse_date(self.request.GET.get('fecha_fin', ''))
        q = self.request.GET.get('q')

        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        if q_cliente:
            queryset = queryset.filter(
                Q(cliente__nombre__icontains=q_cliente)
                | Q(cliente__telefono__icontains=q_cliente)
                | Q(cliente__email__icontains=q_cliente)
                | Q(cliente__nit__icontains=q_cliente)
            )
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_emision__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_emision__lte=fecha_fin)
        if q:
            queryset = queryset.filter(correlativo__icontains=q)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Cliente.objects.order_by('nombre')
        context['estados'] = Cotizacion.ESTADO_CHOICES
        context['show_costs'] = user_can_view_costs(self.request.user)
        return context


class CotizacionCreateView(LoginRequiredMixin, CreateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'cotizaciones_app/cotizacion_form.html'

    def get(self, request, *args, **kwargs):
        self.object = None
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.object = None
        context = super().get_context_data(**kwargs)
        if 'formset' not in context:
            if self.request.POST:
                context['formset'] = CotizacionItemFormSet(self.request.POST, prefix='items')
            else:
                context['formset'] = CotizacionItemFormSet(prefix='items')
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        formset = CotizacionItemFormSet(request.POST, prefix='items')

        # print("=== CREATE POST DEBUG ===")
        # print("has csrf:", "csrfmiddlewaretoken" in request.POST)
        # print("TOTAL_FORMS:", request.POST.get("items-TOTAL_FORMS"))
        # print("INITIAL_FORMS:", request.POST.get("items-INITIAL_FORMS"))
        # print("MIN_NUM_FORMS:", request.POST.get("items-MIN_NUM_FORMS"))
        # print("MAX_NUM_FORMS:", request.POST.get("items-MAX_NUM_FORMS"))
        # print("POST items keys:", [k for k in request.POST.keys() if k.startswith("items-")][:120])
        # print("POST cotizacion keys:", [k for k in request.POST.keys() if not k.startswith("items-")][:80])
        # print("form valid:", form.is_valid())
        # print("form errors:", form.errors)
        # print("formset valid:", formset.is_valid())
        # print("formset non_form_errors:", formset.non_form_errors())
        # print("formset errors:", formset.errors)

        if form.is_valid() and formset.is_valid():
            return self.forms_valid(form, formset)
        return self.forms_invalid(form, formset)

    def forms_invalid(self, form, formset):
        messages.error(self.request, 'Revisa los errores en el formulario.')
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def forms_valid(self, form, formset):
        with transaction.atomic():
            cotizacion = form.save(commit=False)
            cotizacion.fecha_emision = timezone.now().date()
            cotizacion.save()

            formset.instance = cotizacion
            items = formset.save(commit=False)
            for item in items:
                item.cotizacion = cotizacion
                item.precio_venta_unitario = item.producto_servicio.precio_venta
                item.precio_costo_unitario = item.producto_servicio.precio_costo
                if not item.descripcion_editable:
                    item.descripcion_editable = item.producto_servicio.descripcion
                item.save()
            if hasattr(formset, 'deleted_objects'):
                for item in formset.deleted_objects:
                    item.delete()

        messages.success(self.request, 'Cotización creada correctamente.')
        return redirect('cotizaciones:cotizacion_detail', pk=cotizacion.pk)


class CotizacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'cotizaciones_app/cotizacion_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = CotizacionItemFormSet(
                self.request.POST,
                instance=self.object,
                form_kwargs={'show_costs': user_can_view_costs(self.request.user)},
                prefix='items',
            )
        else:
            context['formset'] = CotizacionItemFormSet(
                instance=self.object,
                form_kwargs={'show_costs': user_can_view_costs(self.request.user)},
                prefix='items',
            )
        context['cotizacion'] = self.object
        context['show_costs'] = user_can_view_costs(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        formset = CotizacionItemFormSet(
            request.POST,
            instance=self.object,
            form_kwargs={'show_costs': user_can_view_costs(self.request.user)},
            prefix='items',
        )

        # print("TOTAL_FORMS:", request.POST.get("items-TOTAL_FORMS"))
        # print([k for k in request.POST.keys() if k.startswith("items-")][:50])

        if form.is_valid() and formset.is_valid():
            return self.forms_valid(form, formset)
        return self.forms_invalid(form, formset)

    def forms_invalid(self, form, formset):
        messages.error(self.request, 'Revisa los errores en el formulario.')
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def forms_valid(self, form, formset):
        with transaction.atomic():
            cotizacion = form.save(commit=False)
            cotizacion.fecha_emision = timezone.now().date()
            cotizacion.save()
            for item_form in formset.forms:
                if not item_form.cleaned_data:
                    continue
                if item_form.cleaned_data.get('DELETE') and item_form.instance.pk:
                    item_form.instance.delete()
            items = formset.save(commit=False)
            for item in items:
                item.cotizacion = cotizacion
                item.precio_venta_unitario = item.producto_servicio.precio_venta
                item.precio_costo_unitario = item.producto_servicio.precio_costo
                if not item.descripcion_editable:
                    item.descripcion_editable = item.producto_servicio.descripcion
                item.save()
        messages.success(self.request, 'Cotización actualizada correctamente.')
        return redirect('cotizaciones:cotizacion_detail', pk=cotizacion.pk)


def user_can_view_costs(user):
    return user.is_staff or user.is_superuser


class CotizacionDetailView(LoginRequiredMixin, DetailView):
    model = Cotizacion
    context_object_name = 'cotizacion'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente')

    def get_template_names(self):
        if user_can_view_costs(self.request.user):
            return ['cotizaciones_app/cotizacion_detail_interna.html']
        return ['cotizaciones_app/cotizacion_detail_cliente.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('producto_servicio')
        context['show_costs'] = user_can_view_costs(self.request.user)
        context['institucion'] = Institucion.objects.first()
        try:
            venta = self.object.venta
        except Venta.DoesNotExist:
            venta = None
        context['venta'] = venta
        context['can_convert'] = (
            venta is None
            and self.object.estado in {Cotizacion.ESTADO_BORRADOR, Cotizacion.ESTADO_EMITIDA}
        )
        return context


def _get_cotizacion_context(pk):
    cotizacion = get_object_or_404(Cotizacion.objects.select_related('cliente'), pk=pk)
    items = cotizacion.items.select_related('producto_servicio')
    institucion = Institucion.objects.first()
    return cotizacion, items, institucion


@login_required
@require_POST
def convertir_cotizacion_venta(request, pk):
    cotizacion = get_object_or_404(Cotizacion.objects.select_related('cliente'), pk=pk)
    if cotizacion.estado not in {Cotizacion.ESTADO_BORRADOR, Cotizacion.ESTADO_EMITIDA}:
        messages.error(request, 'La cotización no puede convertirse a venta en su estado actual.')
        return redirect('cotizaciones:cotizacion_detail', pk=cotizacion.pk)
    venta, created = Venta.objects.get_or_create(
        cotizacion=cotizacion,
        defaults={'cliente': cotizacion.cliente, 'fecha_venta': timezone.now().date()},
    )
    if created:
        messages.success(request, 'Cotización convertida a venta correctamente.')
    return redirect('cotizaciones:venta_detail', pk=venta.pk)


@login_required
def cotizacion_cliente_jpg(request, pk):
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    download_jpg = request.GET.get('download') == 'jpg'
    return render(
        request,
        'cotizaciones_app/cotizacion_jpg.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'account_number': '123-456789-0',
            'bank_name': None,
            'show_costs': False,
            'download_jpg': download_jpg,
            'export_mode': download_jpg,
        },
    )


class VentaListView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = 'cotizaciones_app/venta_list.html'
    context_object_name = 'ventas'
    paginate_by = 20

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('cliente', 'cotizacion')
            .order_by('-fecha_venta', '-id')
        )


class VentaDetailView(LoginRequiredMixin, DetailView):
    model = Venta
    template_name = 'cotizaciones_app/venta_detail.html'
    context_object_name = 'venta'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'cotizacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.object
        context['items'] = venta.cotizacion.items.select_related('producto_servicio')
        context['pagos'] = venta.pagos.all()
        context['institucion'] = Institucion.objects.first()
        context['pago_form'] = kwargs.get('pago_form') or PagoVentaForm()
        porcentaje = venta.porcentaje_avance
        context['porcentaje_avance'] = porcentaje if porcentaje <= 100 else 100
        return context


@login_required
@require_POST
def pago_venta_create(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    form = PagoVentaForm(request.POST)
    if form.is_valid():
        pago = form.save(commit=False)
        pago.venta = venta
        pago.save()
        messages.success(request, 'Pago registrado correctamente.')
        return redirect('cotizaciones:venta_detail', pk=venta.pk)
    items = venta.cotizacion.items.select_related('producto_servicio')
    institucion = Institucion.objects.first()
    return render(
        request,
        'cotizaciones_app/venta_detail.html',
        {
            'venta': venta,
            'items': items,
            'pagos': venta.pagos.all(),
            'institucion': institucion,
            'pago_form': form,
            'porcentaje_avance': (
                venta.porcentaje_avance if venta.porcentaje_avance <= 100 else 100
            ),
        },
    )


@login_required
def venta_comprobante_jpg(request, venta_id, pago_id):
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'cotizacion'), pk=venta_id)
    pago = get_object_or_404(PagoVenta, pk=pago_id, venta=venta)
    institucion = Institucion.objects.first()
    download_jpg = request.GET.get('download') == 'jpg'
    return render(
        request,
        'cotizaciones_app/venta_comprobante_jpg.html',
        {
            'venta': venta,
            'pago': pago,
            'institucion': institucion,
            'download_jpg': download_jpg,
            'export_mode': download_jpg,
        },
    )


@login_required
def venta_comprobante_total_jpg(request, venta_id):
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'cotizacion'), pk=venta_id)
    if venta.estado_pago != Venta.ESTADO_PAGADA:
        messages.error(request, 'La venta aún no está totalmente pagada.')
        return redirect('cotizaciones:venta_detail', pk=venta.pk)
    institucion = Institucion.objects.first()
    download_jpg = request.GET.get('download') == 'jpg'
    return render(
        request,
        'cotizaciones_app/venta_comprobante_total_jpg.html',
        {
            'venta': venta,
            'institucion': institucion,
            'download_jpg': download_jpg,
            'export_mode': download_jpg,
        },
    )


@login_required
def venta_certificado_garantia_jpg(request, venta_id):
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'cotizacion'), pk=venta_id)
    if venta.estado_pago != Venta.ESTADO_PAGADA:
        messages.error(request, 'La venta aún no está totalmente pagada.')
        return redirect('cotizaciones:venta_detail', pk=venta.pk)
    institucion = Institucion.objects.first()
    download_jpg = request.GET.get('download') == 'jpg'
    return render(
        request,
        'cotizaciones_app/venta_certificado_garantia_jpg.html',
        {
            'venta': venta,
            'institucion': institucion,
            'download_jpg': download_jpg,
            'export_mode': download_jpg,
        },
    )


@login_required
def producto_precio(request, pk):
    producto = get_object_or_404(ProductoServicio, pk=pk)
    return JsonResponse(
        {
            'precio_venta': str(producto.precio_venta),
            'precio_costo': str(producto.precio_costo),
        }
    )
