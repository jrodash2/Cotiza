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
    path('ventas/', views.VentaListView.as_view(), name='venta_list'),
    path('ventas/<int:pk>/', views.VentaDetailView.as_view(), name='venta_detail'),
    path('ventas/<int:pk>/pagos/', views.pago_venta_create, name='venta_pago_create'),
    path(
        'ventas/<int:venta_id>/comprobante/<int:pago_id>/jpg/',
        views.venta_comprobante_jpg,
        name='venta_comprobante_jpg',
    ),
    path(
        'ventas/<int:venta_id>/comprobante-total/jpg/',
        views.venta_comprobante_total_jpg,
        name='venta_comprobante_total_jpg',
    ),
    path(
        'ventas/<int:venta_id>/certificado-garantia/jpg/',
        views.venta_certificado_garantia_jpg,
        name='venta_certificado_garantia_jpg',
    ),
    path('', views.CotizacionListView.as_view(), name='cotizacion_list'),
    path('nueva/', views.CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('<int:pk>/convertir-a-venta/', views.convertir_cotizacion_venta, name='cotizacion_convertir_venta'),
    path('<int:pk>/', views.CotizacionDetailView.as_view(), name='cotizacion_detail'),
    path('<int:pk>/editar/', views.CotizacionUpdateView.as_view(), name='cotizacion_update'),
    path('producto-precio/<int:pk>/', views.producto_precio, name='producto_precio'),
    path('<int:pk>/jpg/', views.cotizacion_cliente_jpg, name='cotizacion_jpg'),
]
