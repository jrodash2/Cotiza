from django.urls import path

from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.lista_ventas, name='lista_ventas'),
    path('nuevo/', views.crear_venta, name='crear_venta'),
    path('buscar-articulos/', views.buscar_articulos, name='buscar_articulos'),
    path('<int:id>/', views.detalle_venta, name='detalle_venta'),
    path('<int:id>/confirmar/', views.confirmar_venta, name='confirmar_venta'),
    path('<int:id>/anular/', views.anular_venta, name='anular_venta'),
]
