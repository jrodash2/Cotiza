from datetime import datetime, timezone
from venv import logger
from django.forms import IntegerField
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .form import InstitucionForm, UserCreateForm, UserEditForm, PerfilForm
from .models import Perfil, Institucion
from cotizaciones_app.models import Cliente, Cotizacion, Venta
from django.views.generic import CreateView
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import Http404, HttpResponseNotAllowed, JsonResponse
from django.core.exceptions import ValidationError
from django.contrib import messages

from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from django.db import models
from django.db.models import (
    DecimalField,
    Sum,
    Min,
    F,
    Value,
    Count,
    Q,
    Case,
    When,
    OuterRef,
    Subquery,
    IntegerField,
    ExpressionWrapper,
)
from django.contrib.auth.decorators import login_required, user_passes_test
from collections import defaultdict
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
import json
from django.contrib.auth.models import Group
from .utils import grupo_requerido
from django.views.decorators.http import require_GET
from django.db.models.functions import Coalesce
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render

from django.template.loader import render_to_string
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from weasyprint import HTML
from django.db.models.functions import Cast, TruncMonth, TruncWeek
from django.utils import timezone
from datetime import timedelta
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from decimal import Decimal
from servicio_tecnico.models import OrdenServicio, PagoOrdenServicio
from datetime import datetime  
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font
import re


@login_required
@grupo_requerido('Administrador')
def editar_institucion(request):
    institucion = Institucion.objects.first()  # Solo debería haber una

    if request.method == 'POST':
        form = InstitucionForm(request.POST, request.FILES, instance=institucion)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos institucionales actualizados correctamente.")
            return redirect('almacen:editar_institucion')  # Reemplaza con la URL real
    else:
        form = InstitucionForm(instance=institucion)

    return render(request, 'almacen/editar_institucion.html', {'form': form})



@login_required
@grupo_requerido('Administrador', 'Almacen')
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('new_password')
            user.set_password(password)
            user.save()

            group = form.cleaned_data.get('group')
            user.groups.add(group)

            # ✅ Espera a que la señal cree el perfil automáticamente
            foto = form.cleaned_data.get('foto')
            try:
                perfil = user.perfil  # accede al perfil creado por la señal
                if foto:
                    perfil.foto = foto
                    perfil.save()
            except Perfil.DoesNotExist:
                # Fallback solo si la señal falló (raro)
                Perfil.objects.create(user=user, foto=foto)

            messages.success(request, 'Usuario creado correctamente.')
            return redirect('almacen:user_create')
    else:
        form = UserCreateForm()

    users = User.objects.all()
    return render(request, 'almacen/user_form_create.html', {'form': form, 'users': users})

@login_required
@grupo_requerido('Administrador', 'Almacen')
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    try:
        perfil = user.perfil
    except Perfil.DoesNotExist:
        perfil = Perfil(user=user)

    if request.method == 'POST':
        form_user = UserEditForm(request.POST, instance=user)
        form_perfil = PerfilForm(request.POST, request.FILES, instance=perfil)
        if form_user.is_valid() and form_perfil.is_valid():
            user = form_user.save(commit=False)
            user.save()

            # Actualizar grupo: limpiar y agregar el nuevo grupo
            group = form_user.cleaned_data.get('group')
            if group:
                user.groups.clear()
                user.groups.add(group)

            perfil = form_perfil.save(commit=False)
            perfil.user = user
            perfil.save()

            messages.success(request, 'Usuario editado correctamente.')
            return redirect('almacen:user_create')
    else:
        form_user = UserEditForm(instance=user)
        form_perfil = PerfilForm(instance=perfil)

    context = {
        'form': form_user,
        'perfil_form': form_perfil,
        'users': User.objects.all(),
    }
    return render(request, 'almacen/user_form_edit.html', context)



@login_required
@grupo_requerido('Administrador', 'Almacen')
def perfil_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    try:
        perfil = user.perfil
    except Perfil.DoesNotExist:
        perfil = Perfil(user=user)
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('almacen:user_edit', user_id=user.id)
    else:
        form = PerfilForm(instance=perfil)
    
    return render(request, 'almacen/perfil_edit.html', {'form': form, 'user': user})

@login_required
@grupo_requerido('Administrador', 'Almacen')
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('almacen:user_create')  # Redirige a la misma página para mostrar la lista actualizada
    return render(request, 'almacen/user_confirm_delete.html', {'user': user})


def home(request):
    return render(request, 'almacen/login.html')

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum
import json

@login_required
@grupo_requerido('Administrador', 'Almacen')
def dahsboard(request):
    ventas_qs = Venta.objects.select_related('cotizacion', 'cliente').exclude(
        cotizacion__estado=Cotizacion.ESTADO_ANULADA,
    )
    ordenes_qs = OrdenServicio.objects.select_related('cliente', 'tecnico_asignado').prefetch_related('pagos', 'cotizaciones_servicio')
    pagos_servicio_qs = PagoOrdenServicio.objects.filter(activo=True).select_related('orden_servicio', 'usuario_registro')

    current_year = timezone.now().year
    today = timezone.localdate()
    month_labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    monthly_sales_amounts = [0.0] * 12
    for venta in ventas_qs.filter(fecha_venta__year=current_year):
        month = venta.fecha_venta
        if month:
            monthly_sales_amounts[month.month - 1] += float(venta.total or 0)

    clientes_por_mes_data = [0] * 12
    if 'created_at' in {field.name for field in Cliente._meta.get_fields()}:
        clientes_fechas = Cliente.objects.filter(created_at__year=current_year).values_list('created_at', flat=True)
    else:
        clientes_fechas = Cliente.objects.annotate(fecha_registro=Min('cotizaciones__fecha_emision')).values_list('fecha_registro', flat=True)
    for fecha in clientes_fechas:
        if fecha and getattr(fecha, 'year', None) == current_year:
            clientes_por_mes_data[fecha.month - 1] += 1

    totals = {
        'clientes': Cliente.objects.count(),
        'ventas_monto': Decimal('0.00'),
        'pendiente_pago': Decimal('0.00'),
    }
    for venta in ventas_qs:
        total_venta = venta.total or Decimal('0.00')
        saldo = venta.saldo or Decimal('0.00')
        totals['ventas_monto'] += total_venta
        if venta.estado_pago != Venta.ESTADO_PAGADA and saldo > 0:
            totals['pendiente_pago'] += saldo

    def fmt_q(value):
        if value is None:
            value = Decimal('0.00')
        return f"Q{value:,.2f}"

    estado_counts = dict(ordenes_qs.values_list('estado').annotate(total=Count('id')))
    servicio_estados_resumen = [
        {'label': 'Recibidas hoy', 'value': ordenes_qs.filter(fecha_recepcion__date=today).count(), 'color': 'primary'},
        {'label': 'En diagnóstico', 'value': estado_counts.get(OrdenServicio.Estado.EN_DIAGNOSTICO, 0), 'color': 'info'},
        {'label': 'Pendientes de cotización', 'value': estado_counts.get(OrdenServicio.Estado.PENDIENTE_COTIZACION, 0), 'color': 'warning'},
        {'label': 'Cotizadas', 'value': estado_counts.get(OrdenServicio.Estado.COTIZADO, 0), 'color': 'secondary'},
        {'label': 'Aprobadas reparación', 'value': estado_counts.get(OrdenServicio.Estado.APROBADO_REPARACION, 0), 'color': 'success'},
        {'label': 'En reparación', 'value': estado_counts.get(OrdenServicio.Estado.EN_REPARACION, 0), 'color': 'primary'},
        {'label': 'Listas para entregar', 'value': estado_counts.get(OrdenServicio.Estado.LISTO_PARA_ENTREGAR, 0), 'color': 'success'},
        {'label': 'Entregadas', 'value': estado_counts.get(OrdenServicio.Estado.ENTREGADO, 0), 'color': 'dark'},
    ]

    ordenes_con_saldo = []
    total_base_servicio = Decimal('0.00')
    total_pagado_servicio = Decimal('0.00')
    saldo_pendiente_servicio = Decimal('0.00')
    for orden in ordenes_qs:
        base = orden.get_total_base_cobro()
        pagado = orden.get_total_pagado()
        saldo = max(base - pagado, Decimal('0.00'))
        total_base_servicio += base
        total_pagado_servicio += pagado
        saldo_pendiente_servicio += saldo
        if saldo > 0:
            ordenes_con_saldo.append(orden)

    ingresos_hoy_servicio = pagos_servicio_qs.filter(fecha__date=today).aggregate(total=Coalesce(Sum('monto'), Value(Decimal('0.00')), output_field=DecimalField(max_digits=12, decimal_places=2)))['total']
    ingresos_mes_servicio = pagos_servicio_qs.filter(fecha__year=today.year, fecha__month=today.month).aggregate(total=Coalesce(Sum('monto'), Value(Decimal('0.00')), output_field=DecimalField(max_digits=12, decimal_places=2)))['total']

    ordenes_por_estado_labels = []
    ordenes_por_estado_totals = []
    for estado, label in OrdenServicio.Estado.choices:
        total = estado_counts.get(estado, 0)
        if total:
            ordenes_por_estado_labels.append(label)
            ordenes_por_estado_totals.append(total)

    pagos_servicio_mes = [0.0] * 12
    for pago in pagos_servicio_qs.filter(fecha__year=current_year):
        pagos_servicio_mes[pago.fecha.month - 1] += float(pago.monto or 0)

    context = {
        'totals': totals,
        'total_ventas_fmt': fmt_q(totals['ventas_monto']),
        'total_pendiente_fmt': fmt_q(totals['pendiente_pago']),
        'chart_month_labels': month_labels,
        'chart_month_sales': monthly_sales_amounts,
        'clientes_por_mes_labels': month_labels,
        'clientes_por_mes_data': clientes_por_mes_data,
        'servicio_estados_resumen': servicio_estados_resumen,
        'servicio_economico': {
            'total_cotizado': fmt_q(total_base_servicio),
            'total_pagado': fmt_q(total_pagado_servicio),
            'saldo_pendiente': fmt_q(saldo_pendiente_servicio),
            'ingresos_hoy': fmt_q(ingresos_hoy_servicio),
            'ingresos_mes': fmt_q(ingresos_mes_servicio),
            'ordenes_con_saldo': len(ordenes_con_saldo),
        },
        'ultimas_ordenes_servicio': ordenes_qs.order_by('-fecha_recepcion', '-id')[:5],
        'ordenes_pendientes_pago': ordenes_con_saldo[:5],
        'ordenes_por_estado_labels': ordenes_por_estado_labels,
        'ordenes_por_estado_totals': ordenes_por_estado_totals,
        'pagos_servicio_mes': pagos_servicio_mes,
    }

    return render(request, 'almacen/dashboard.html', context)




def signout(request):
    logout(request)
    return redirect('almacen:signin')


def signin(request):  
    institucion = Institucion.objects.first()
    if request.method == 'GET':
        # Deberías instanciar el AuthenticationForm correctamente
        return render(request, 'almacen/login.html', {
            'form': AuthenticationForm(),
            'institucion': institucion,
        })
    else:
        # Se instancia AuthenticationForm con los datos del POST para mantener el estado
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            # El método authenticate devuelve el usuario si es válido
            user = form.get_user()
            
            # Si el usuario es encontrado, se inicia sesión
            auth_login(request, user)
            
            # Ahora verificamos los grupos
            for g in user.groups.all():
                print(g.name)
                if g.name == 'Administrador':
                    return redirect('almacen:dahsboard')
                elif g.name == 'Departamento':
                    return redirect('almacen:crear_requerimiento')
                elif g.name == 'Almacen':
                    return redirect('almacen:dahsboard')
            # Si no se encuentra el grupo adecuado, se redirige a una página por defecto
            return redirect('dahsboard')
        else:
            # Si el formulario no es válido, se retorna con el error
            return render(request, 'almacen/login.html', {
                'form': form,  # Pasamos el formulario con los errores
                'error': 'Usuario o contraseña incorrectos',
                'institucion': institucion,
            })



def acceso_denegado(request, exception=None):
    return render(request, 'scompras/403.html', status=403)
