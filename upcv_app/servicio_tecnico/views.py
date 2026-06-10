from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from weasyprint import HTML

from almacen_app.models import Institucion
from .forms import (
    PagoOrdenServicioForm,
    CambioEstadoForm,
    CotizacionServicioForm,
    DetalleCotizacionFormSet,
    EntregaOrdenForm,
    OrdenServicioForm,
    SeguimientoOrdenServicioForm,
)
from .models import CotizacionServicio, OrdenServicio, PagoOrdenServicio


ROLES_SERVICIO = ('Administrador', 'Recepcion', 'Técnico', 'Tecnico', 'Almacen')
ROLES_ADMINISTRATIVOS = ('Administrador', 'Recepcion', 'Almacen')
ROLES_TECNICOS = ('Administrador', 'Técnico', 'Tecnico')


def usuario_en_roles(user, roles=ROLES_SERVICIO):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name__in=roles).exists())


class RolServicioMixin(UserPassesTestMixin):
    roles = ROLES_SERVICIO

    def test_func(self):
        return usuario_en_roles(self.request.user, self.roles)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return redirect('almacen:acceso_denegado')


def roles_requeridos(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not usuario_en_roles(request.user, roles):
                return redirect('almacen:acceso_denegado')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


class OrdenServicioListView(LoginRequiredMixin, RolServicioMixin, ListView):
    model = OrdenServicio
    template_name = 'servicio_tecnico/orden_list.html'
    context_object_name = 'ordenes'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('cliente', 'tecnico_asignado').prefetch_related('pagos', 'cotizaciones_servicio')
        q = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '')
        tecnico = self.request.GET.get('tecnico', '')
        tipo_equipo = self.request.GET.get('tipo_equipo', '').strip()
        fecha_inicio = parse_date(self.request.GET.get('fecha_inicio', ''))
        fecha_fin = parse_date(self.request.GET.get('fecha_fin', ''))
        if q:
            qs = qs.filter(Q(numero_orden__icontains=q) | Q(cliente__nombre__icontains=q) | Q(cliente__nit__icontains=q) | Q(numero_serie__icontains=q))
        if estado:
            qs = qs.filter(estado=estado)
        if tecnico:
            qs = qs.filter(tecnico_asignado_id=tecnico)
        if tipo_equipo:
            qs = qs.filter(tipo_equipo__icontains=tipo_equipo)
        if fecha_inicio:
            qs = qs.filter(fecha_recepcion__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_recepcion__date__lte=fecha_fin)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = OrdenServicio.Estado.choices
        context['tecnicos'] = OrdenServicio._meta.get_field('tecnico_asignado').remote_field.model.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
        return context


class OrdenServicioCreateView(LoginRequiredMixin, RolServicioMixin, CreateView):
    roles = ROLES_ADMINISTRATIVOS
    model = OrdenServicio
    form_class = OrdenServicioForm
    template_name = 'servicio_tecnico/orden_form.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.usuario_creacion = self.request.user
        self.object.save(usuario_historial=self.request.user, observacion_historial='Equipo recibido y orden creada.')
        form.save_m2m()
        messages.success(self.request, f'Orden {self.object.numero_orden} creada correctamente.')
        return redirect(self.object)


class OrdenServicioUpdateView(LoginRequiredMixin, RolServicioMixin, UpdateView):
    model = OrdenServicio
    form_class = OrdenServicioForm
    template_name = 'servicio_tecnico/orden_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Orden actualizada correctamente.')
        return super().form_valid(form)


class OrdenServicioDetailView(LoginRequiredMixin, RolServicioMixin, DetailView):
    model = OrdenServicio
    template_name = 'servicio_tecnico/orden_detail.html'
    context_object_name = 'orden'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'tecnico_asignado', 'usuario_creacion').prefetch_related('seguimientos__usuario', 'historial_estados__usuario', 'cotizaciones_servicio', 'pagos__usuario_registro')


@roles_requeridos(*ROLES_TECNICOS)
def agregar_seguimiento(request, pk):
    orden = get_object_or_404(OrdenServicio, pk=pk)
    form = SeguimientoOrdenServicioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        seguimiento = form.save(commit=False)
        seguimiento.orden_servicio = orden
        seguimiento.usuario = request.user
        seguimiento.save()
        messages.success(request, 'Seguimiento técnico agregado.')
        return redirect(orden)
    return render(request, 'servicio_tecnico/accion_form.html', {'form': form, 'orden': orden, 'titulo': 'Agregar seguimiento'})


@roles_requeridos(*ROLES_SERVICIO)
def cambiar_estado(request, pk):
    orden = get_object_or_404(OrdenServicio, pk=pk)
    form = CambioEstadoForm(request.POST or None, instance=orden)
    if request.method == 'POST' and form.is_valid():
        orden = form.save(commit=False)
        if orden.estado == OrdenServicio.Estado.ENTREGADO:
            messages.error(request, 'Use la acción Registrar entrega para cerrar la orden.')
        else:
            orden.save(usuario_historial=request.user, observacion_historial=form.cleaned_data['observacion'])
            messages.success(request, 'Estado actualizado correctamente.')
            return redirect(orden)
    return render(request, 'servicio_tecnico/accion_form.html', {'form': form, 'orden': orden, 'titulo': 'Cambiar estado'})


@roles_requeridos(*ROLES_ADMINISTRATIVOS)
def registrar_entrega(request, pk):
    orden = get_object_or_404(OrdenServicio, pk=pk)
    form = EntregaOrdenForm(request.POST or None, instance=orden)
    if request.method == 'POST' and form.is_valid():
        orden = form.save(commit=False)
        orden.estado = OrdenServicio.Estado.ENTREGADO
        orden.fecha_entrega = timezone.now()
        orden.save(usuario_historial=request.user, observacion_historial=f'Equipo entregado a {orden.recibido_por}. {orden.observaciones_entrega}'.strip())
        messages.success(request, 'Entrega registrada y orden cerrada.')
        return redirect(orden)
    return render(request, 'servicio_tecnico/accion_form.html', {'form': form, 'orden': orden, 'titulo': 'Registrar entrega final'})


@roles_requeridos(*ROLES_ADMINISTRATIVOS)
def registrar_pago(request, pk):
    orden = get_object_or_404(OrdenServicio, pk=pk)
    if not orden.puede_registrar_pago:
        messages.error(request, 'La orden no admite pagos o no tiene saldo pendiente.')
        return redirect(orden)
    pago = PagoOrdenServicio(orden_servicio=orden, usuario_registro=request.user)
    form = PagoOrdenServicioForm(request.POST or None, instance=pago)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            orden_bloqueada = OrdenServicio.objects.select_for_update().get(pk=orden.pk)
            if not orden_bloqueada.puede_registrar_pago:
                messages.error(request, 'La orden cambió y ya no admite este pago.')
                return redirect(orden_bloqueada)
            form.instance.orden_servicio = orden_bloqueada
            pago = form.save()
        messages.success(request, f'Pago {pago.numero_recibo} registrado correctamente.')
        return redirect('servicio_tecnico:pago_recibo_pdf', pk=pago.pk)
    return render(request, 'servicio_tecnico/pago_form.html', {'form': form, 'orden': orden})


@roles_requeridos('Administrador')
def anular_pago(request, pk):
    pago = get_object_or_404(PagoOrdenServicio, pk=pk, activo=True)
    if request.method == 'POST':
        pago.activo = False
        pago.fecha_anulacion = timezone.now()
        pago.usuario_anulacion = request.user
        pago.save(update_fields=['activo', 'fecha_anulacion', 'usuario_anulacion'])
        messages.success(request, f'Pago {pago.numero_recibo} anulado correctamente.')
    return redirect(pago.orden_servicio)


def guardar_cotizacion(request, orden, instance=None):
    form = CotizacionServicioForm(request.POST or None, instance=instance)
    formset = DetalleCotizacionFormSet(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            cotizacion = form.save(commit=False)
            cotizacion.orden_servicio = orden
            if not cotizacion.pk:
                cotizacion.usuario_creacion = request.user
            cotizacion.save()
            formset.instance = cotizacion
            formset.save()
            cotizacion.actualizar_totales()
            if orden.estado == OrdenServicio.Estado.PENDIENTE_COTIZACION:
                orden.estado = OrdenServicio.Estado.COTIZADO
                orden.save(usuario_historial=request.user, observacion_historial=f'Cotización {cotizacion.numero_cotizacion} creada.')
        messages.success(request, 'Cotización guardada correctamente.')
        return redirect('servicio_tecnico:cotizacion_detalle', pk=cotizacion.pk)
    return render(request, 'servicio_tecnico/cotizacion_form.html', {'form': form, 'formset': formset, 'orden': orden, 'cotizacion': instance})


@roles_requeridos(*ROLES_ADMINISTRATIVOS)
def crear_cotizacion(request, orden_pk):
    return guardar_cotizacion(request, get_object_or_404(OrdenServicio, pk=orden_pk))


@roles_requeridos(*ROLES_ADMINISTRATIVOS)
def editar_cotizacion(request, pk):
    cotizacion = get_object_or_404(CotizacionServicio, pk=pk)
    return guardar_cotizacion(request, cotizacion.orden_servicio, cotizacion)


class CotizacionServicioDetailView(LoginRequiredMixin, RolServicioMixin, DetailView):
    model = CotizacionServicio
    template_name = 'servicio_tecnico/cotizacion_detail.html'
    context_object_name = 'cotizacion'

    def get_queryset(self):
        return super().get_queryset().select_related('orden_servicio__cliente', 'usuario_creacion').prefetch_related('detalles', 'orden_servicio__pagos')


@roles_requeridos(*ROLES_ADMINISTRATIVOS)
def decidir_cotizacion(request, pk, decision):
    cotizacion = get_object_or_404(CotizacionServicio, pk=pk)
    if request.method != 'POST' or decision not in ('aprobar', 'rechazar'):
        return redirect('servicio_tecnico:cotizacion_detalle', pk=pk)
    aprobada = decision == 'aprobar'
    cotizacion.estado = CotizacionServicio.Estado.APROBADA if aprobada else CotizacionServicio.Estado.RECHAZADA
    cotizacion.save(update_fields=['estado', 'fecha_actualizacion'])
    orden = cotizacion.orden_servicio
    orden.estado = OrdenServicio.Estado.APROBADO_REPARACION if aprobada else OrdenServicio.Estado.NO_REPARADO
    orden.save(usuario_historial=request.user, observacion_historial=f'Cotización {cotizacion.numero_cotizacion} {cotizacion.get_estado_display().lower()}.')
    messages.success(request, f'Cotización {cotizacion.get_estado_display().lower()}.')
    return redirect('servicio_tecnico:cotizacion_detalle', pk=pk)


def _get_logo_url(request, institucion):
    if not institucion or not institucion.logo:
        return None
    return request.build_absolute_uri(institucion.logo.url)


def render_pdf(request, template, context, filename):
    context = {**context}
    institucion = context.get('institucion') or Institucion.objects.first()
    context.setdefault('institucion', institucion)
    context.setdefault('logo_url', _get_logo_url(request, institucion))
    html = render_to_string(template, context, request=request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf(response)
    return response


@roles_requeridos(*ROLES_SERVICIO)
def constancia_recepcion_pdf(request, pk):
    orden = get_object_or_404(OrdenServicio.objects.select_related('cliente', 'tecnico_asignado').prefetch_related('pagos'), pk=pk)
    return render_pdf(request, 'servicio_tecnico/pdf/constancia_recepcion.html', {'orden': orden}, f'{orden.numero_orden}-recepcion.pdf')


@roles_requeridos(*ROLES_SERVICIO)
def cotizacion_pdf(request, pk):
    cotizacion = get_object_or_404(CotizacionServicio.objects.select_related('orden_servicio__cliente').prefetch_related('detalles', 'orden_servicio__pagos'), pk=pk)
    return render_pdf(request, 'servicio_tecnico/pdf/cotizacion.html', {'cotizacion': cotizacion}, f'{cotizacion.numero_cotizacion}.pdf')


@roles_requeridos(*ROLES_SERVICIO)
def pago_recibo_pdf(request, pk):
    pago = get_object_or_404(PagoOrdenServicio.objects.select_related('orden_servicio__cliente', 'orden_servicio__tecnico_asignado', 'usuario_registro', 'usuario_anulacion'), pk=pk)
    return render_pdf(request, 'servicio_tecnico/pdf/recibo_pago.html', {'pago': pago, 'orden': pago.orden_servicio}, f'{pago.numero_recibo}.pdf')
