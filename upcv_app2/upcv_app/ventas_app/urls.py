from django.urls import path

from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.lista_ventas, name='lista_ventas'),
    path('nuevo/', views.crear_venta, name='crear_venta'),
    path('ajax/buscar-items/', views.buscar_items, name='buscar_items'),
    path('ajax/item/<str:item_type>/<int:item_id>/', views.item_detail, name='item_detail'),
    path('<int:id>/', views.detalle_venta, name='detalle_venta'),
    path('<int:id>/confirmar/', views.confirmar_venta, name='confirmar_venta'),
    path('<int:id>/anular/', views.anular_venta, name='anular_venta'),
]
