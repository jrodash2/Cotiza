from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from weasyprint import HTML

from almacen_app.models import Institucion

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
    success_url = reverse_lazy('cotizaciones_app:cliente_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente creado correctamente.')
        return super().form_valid(form)


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cotizaciones_app/cliente_form.html'
    success_url = reverse_lazy('cotizaciones_app:cliente_list')

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
    success_url = reverse_lazy('cotizaciones_app:producto_list')

    def form_valid(self, form):
        messages.success(self.request, 'Producto/servicio creado correctamente.')
        return super().form_valid(form)


class ProductoServicioUpdateView(LoginRequiredMixin, UpdateView):
    model = ProductoServicio
    form_class = ProductoServicioForm
    template_name = 'cotizaciones_app/producto_form.html'
    success_url = reverse_lazy('cotizaciones_app:producto_list')

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
        estado = self.request.GET.get('estado')
        fecha_inicio = parse_date(self.request.GET.get('fecha_inicio', ''))
        fecha_fin = parse_date(self.request.GET.get('fecha_fin', ''))
        q = self.request.GET.get('q')

        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
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
        context['show_costs'] = self.request.user.is_staff
        return context


class CotizacionCreateView(LoginRequiredMixin, View):
    template_name = 'cotizaciones_app/cotizacion_form.html'

    def get(self, request):
        form = CotizacionForm()
        formset = CotizacionItemFormSet(form_kwargs={'show_costs': request.user.is_staff})
        return render(
            request,
            self.template_name,
            {'form': form, 'formset': formset, 'show_costs': request.user.is_staff},
        )

    def post(self, request):
        form = CotizacionForm(request.POST)
        formset = CotizacionItemFormSet(request.POST, form_kwargs={'show_costs': request.user.is_staff})
        if form.is_valid() and formset.is_valid():
            cotizacion = form.save()
            formset.instance = cotizacion
            formset.save()
            messages.success(request, 'Cotización creada correctamente.')
            return redirect('cotizaciones_app:cotizacion_detail', pk=cotizacion.pk)
        messages.error(request, 'Revisa los errores en el formulario.')
        return render(
            request,
            self.template_name,
            {'form': form, 'formset': formset, 'show_costs': request.user.is_staff},
        )


class CotizacionUpdateView(LoginRequiredMixin, View):
    template_name = 'cotizaciones_app/cotizacion_form.html'

    def get(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        form = CotizacionForm(instance=cotizacion)
        formset = CotizacionItemFormSet(
            instance=cotizacion,
            form_kwargs={'show_costs': request.user.is_staff},
        )
        return render(
            request,
            self.template_name,
            {'form': form, 'formset': formset, 'cotizacion': cotizacion, 'show_costs': request.user.is_staff},
        )

    def post(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        form = CotizacionForm(request.POST, instance=cotizacion)
        formset = CotizacionItemFormSet(
            request.POST,
            instance=cotizacion,
            form_kwargs={'show_costs': request.user.is_staff},
        )
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Cotización actualizada correctamente.')
            return redirect('cotizaciones_app:cotizacion_detail', pk=cotizacion.pk)
        messages.error(request, 'Revisa los errores en el formulario.')
        return render(
            request,
            self.template_name,
            {'form': form, 'formset': formset, 'cotizacion': cotizacion, 'show_costs': request.user.is_staff},
        )


@login_required
def cotizacion_detail(request, pk):
    cotizacion = get_object_or_404(Cotizacion.objects.select_related('cliente'), pk=pk)
    items = cotizacion.items.select_related('producto_servicio')
    return render(
        request,
        'cotizaciones_app/cotizacion_detail.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'show_costs': request.user.is_staff,
        },
    )


@login_required
def cotizacion_print(request, pk):
    cotizacion = get_object_or_404(Cotizacion.objects.select_related('cliente'), pk=pk)
    items = cotizacion.items.select_related('producto_servicio')
    institucion = Institucion.objects.first()
    download_jpg = request.GET.get('download') == 'jpg'
    return render(
        request,
        'cotizaciones_app/cotizacion_print.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'show_costs': request.user.is_staff,
            'download_jpg': download_jpg,
        },
    )


@login_required
def cotizacion_pdf(request, pk):
    cotizacion = get_object_or_404(Cotizacion.objects.select_related('cliente'), pk=pk)
    items = cotizacion.items.select_related('producto_servicio')
    institucion = Institucion.objects.first()
    html_string = render_to_string(
        'cotizaciones_app/cotizacion_print.html',
        {
            'cotizacion': cotizacion,
            'items': items,
            'institucion': institucion,
            'show_costs': request.user.is_staff,
            'download_jpg': False,
        },
        request=request,
    )
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"cotizacion_{cotizacion.correlativo}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
