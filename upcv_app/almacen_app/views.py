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
from cotizaciones_app.models import Cliente, Cotizacion, CotizacionItem, ProductoServicio, Venta
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
    cotizaciones_qs = Cotizacion.objects.select_related('cliente')
    ventas_qs = Venta.objects.select_related('cotizacion', 'cliente')

    current_year = timezone.now().year
    monthly_sales_stats = (
        ventas_qs.filter(fecha_venta__year=current_year)
        .annotate(month=TruncMonth('fecha_venta'))
        .values('month')
        .annotate(
            total_amount=Coalesce(
                Sum('cotizacion__subtotal_venta'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .order_by('month')
    )

    month_labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    monthly_sales_amounts = [0.0] * 12
    for item in monthly_sales_stats:
        month = item['month']
        if not month:
            continue
        monthly_sales_amounts[month.month - 1] = float(item['total_amount'] or 0)

    top_clients = (
        cotizaciones_qs.values('cliente__nombre')
        .annotate(
            total_amount=Coalesce(
                Sum('subtotal_venta'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .order_by('-total_amount')[:5]
    )
    top_clients_labels = [item['cliente__nombre'] or 'Sin cliente' for item in top_clients]
    top_clients_amounts = [float(item['total_amount'] or 0) for item in top_clients]

    totals = {
        'cotizaciones': cotizaciones_qs.count(),
        'ventas': ventas_qs.count(),
        'clientes': Cliente.objects.count(),
        'productos': ProductoServicio.objects.count(),
        'ventas_monto': ventas_qs.filter(fecha_venta__year=current_year).aggregate(
            total=Coalesce(
                Sum('cotizacion__subtotal_venta'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )['total'],
        'monto': cotizaciones_qs.aggregate(
            total=Coalesce(
                Sum('subtotal_venta'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )['total'],
    }

    def fmt_q(value):
        if value is None:
            value = Decimal('0.00')
        return f"Q{value:,.2f}"

    top_productos = (
        CotizacionItem.objects.select_related('producto_servicio')
        .filter(cotizacion__venta__isnull=False)
        .values('producto_servicio__nombre')
        .annotate(
            total_monto=Coalesce(
                Sum('total_linea_venta'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
            total_cantidad=Coalesce(
                Sum('cantidad'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
        )
        .order_by('-total_monto')[:10]
    )
    top_productos_labels = [
        item['producto_servicio__nombre'] or 'SIN NOMBRE'
        for item in top_productos
    ]
    top_productos_totals = [float(item['total_monto'] or Decimal('0.00')) for item in top_productos]

    context = {
        'totals': totals,
        'total_cotizado_fmt': fmt_q(totals['monto']),
        'total_ventas_fmt': fmt_q(totals['ventas_monto']),
        'chart_month_labels': month_labels,
        'chart_month_sales': monthly_sales_amounts,
        'chart_month_totals': monthly_sales_amounts,
        'top_clients_labels': top_clients_labels,
        'top_clients_totals': top_clients_amounts,
        'top_products_labels': top_productos_labels,
        'top_products_totals': top_productos_totals,
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
