from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
import os

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from xhtml2pdf import pisa

from almacen_app.models import Institucion
from django.contrib.staticfiles import finders

from .forms import (
    ClienteForm,
    ProductoServicioForm,
    CotizacionForm,
    CotizacionItemFormSet,
)
from .models import Cliente, ProductoServicio, Cotizacion


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
        return context


def _get_cotizacion_context(pk):
    cotizacion = get_object_or_404(Cotizacion.objects.select_related('cliente'), pk=pk)
    items = cotizacion.items.select_related('producto_servicio')
    institucion = Institucion.objects.first()
    return cotizacion, items, institucion


def link_callback(uri, rel):
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = finders.find(uri.replace(settings.STATIC_URL, ""))
        if path is None:
            path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        return uri

    if not path or not os.path.isfile(path):
        return uri

    return path


def _require_staff(user):
    if not user_can_view_costs(user):
        raise PermissionDenied


@login_required
def cotizacion_print(request, pk):
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    download_jpg = request.GET.get('download') == 'jpg'
    logo_url = _get_logo_url(request, for_pdf=False)
    return render(
        request,
        'cotizaciones_app/cotizacion_cliente_jpg.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'account_number': '123-456789-0',
            'bank_name': None,
            'show_costs': False,
            'download_jpg': download_jpg,
            'is_internal': False,
            'is_jpg': download_jpg,
        },
    )


@login_required
def cotizacion_pdf(request, pk):
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    html_string = render_to_string(
        'cotizaciones_app/cotizacion_cliente_pdf.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'account_number': '123-456789-0',
            'bank_name': None,
            'show_costs': False,
            'download_jpg': False,
            'is_internal': False,
            'is_jpg': False,
        },
        request=request,
    )
    response = HttpResponse(content_type='application/pdf')
    pisa.CreatePDF(html_string, dest=response, link_callback=link_callback)
    filename = f"cotizacion_{cotizacion.correlativo}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def cotizacion_cliente_jpg(request, pk):
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    return render(
        request,
        'cotizaciones_app/cotizacion_cliente_jpg.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'account_number': '123-456789-0',
            'bank_name': None,
            'show_costs': False,
            'download_jpg': True,
            'is_internal': False,
            'is_jpg': True,
        },
    )


@login_required
def cotizacion_pdf_interno(request, pk):
    _require_staff(request.user)
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    html_string = render_to_string(
        'cotizaciones_app/cotizacion_print.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'show_costs': True,
            'download_jpg': False,
            'is_internal': True,
            'is_jpg': False,
        },
        request=request,
    )
    response = HttpResponse(content_type='application/pdf')
    pisa.CreatePDF(html_string, dest=response, link_callback=link_callback)
    filename = f"cotizacion_{cotizacion.correlativo}_interna.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def cotizacion_jpg_interno(request, pk):
    _require_staff(request.user)
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    return render(
        request,
        'cotizaciones_app/cotizacion_cliente_jpg.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'account_number': '123-456789-0',
            'bank_name': None,
            'show_costs': False,
            'download_jpg': download_jpg,
            'is_internal': False,
            'is_jpg': download_jpg,
        },
    )


@login_required
def cotizacion_pdf(request, pk):
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    html_string = render_to_string(
        'cotizaciones_app/cotizacion_cliente_pdf.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'account_number': '123-456789-0',
            'bank_name': None,
            'show_costs': False,
            'download_jpg': False,
            'is_internal': False,
            'is_jpg': False,
        },
        request=request,
    )
    response = HttpResponse(content_type='application/pdf')
    pisa.CreatePDF(html_string, dest=response, link_callback=link_callback)
    filename = f"cotizacion_{cotizacion.correlativo}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def cotizacion_cliente_jpg(request, pk):
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    return render(
        request,
        'cotizaciones_app/cotizacion_cliente_jpg.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'account_number': '123-456789-0',
            'bank_name': None,
            'show_costs': False,
            'download_jpg': True,
            'is_internal': False,
            'is_jpg': True,
        },
    )


@login_required
def cotizacion_pdf_interno(request, pk):
    _require_staff(request.user)
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    html_string = render_to_string(
        'cotizaciones_app/cotizacion_print.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'show_costs': True,
            'download_jpg': False,
            'is_internal': True,
            'is_jpg': False,
        },
        request=request,
    )
    response = HttpResponse(content_type='application/pdf')
    pisa.CreatePDF(html_string, dest=response, link_callback=link_callback)
    filename = f"cotizacion_{cotizacion.correlativo}_interna.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def cotizacion_jpg_interno(request, pk):
    _require_staff(request.user)
    cotizacion, items, institucion = _get_cotizacion_context(pk)
    return render(
        request,
        'cotizaciones_app/cotizacion_print.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'show_costs': True,
            'download_jpg': True,
            'is_internal': True,
            'is_jpg': True,
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
