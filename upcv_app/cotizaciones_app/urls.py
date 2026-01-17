from django.urls import path

from . import views


app_name = 'cotizaciones'

urlpatterns = [
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('productos/', views.ProductoServicioListView.as_view(), name='producto_list'),
    path('productos/nuevo/', views.ProductoServicioCreateView.as_view(), name='producto_create'),
    path('productos/<int:pk>/editar/', views.ProductoServicioUpdateView.as_view(), name='producto_update'),
    path('', views.CotizacionListView.as_view(), name='cotizacion_list'),
    path('nueva/', views.CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('<int:pk>/', views.CotizacionDetailView.as_view(), name='cotizacion_detail'),
    path('<int:pk>/editar/', views.CotizacionUpdateView.as_view(), name='cotizacion_update'),
    path('producto-precio/<int:pk>/', views.producto_precio, name='producto_precio'),
    path('<int:pk>/pdf/', views.cotizacion_pdf, name='cotizacion_pdf'),
    path('<int:pk>/jpg/', views.cotizacion_cliente_jpg, name='cotizacion_jpg'),
    path('<int:pk>/print/', views.cotizacion_print, name='cotizacion_print'),
    path('<int:pk>/pdf-interno/', views.cotizacion_pdf_interno, name='cotizacion_pdf_interno'),
    path('<int:pk>/jpg-interno/', views.cotizacion_jpg_interno, name='cotizacion_jpg_interno'),
]
