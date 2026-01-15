from django.urls import path

from . import views


app_name = 'cotizaciones_app'

urlpatterns = [
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('productos/', views.ProductoServicioListView.as_view(), name='producto_list'),
    path('productos/nuevo/', views.ProductoServicioCreateView.as_view(), name='producto_create'),
    path('productos/<int:pk>/editar/', views.ProductoServicioUpdateView.as_view(), name='producto_update'),
    path('', views.CotizacionListView.as_view(), name='cotizacion_list'),
    path('nueva/', views.CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('<int:pk>/', views.cotizacion_detail, name='cotizacion_detail'),
    path('<int:pk>/editar/', views.CotizacionUpdateView.as_view(), name='cotizacion_update'),
    path('<int:pk>/pdf/', views.cotizacion_pdf, name='cotizacion_pdf'),
    path('<int:pk>/print/', views.cotizacion_print, name='cotizacion_print'),
]
