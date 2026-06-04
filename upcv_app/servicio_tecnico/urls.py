from django.urls import path

from . import views

app_name = 'servicio_tecnico'

urlpatterns = [
    path('', views.OrdenServicioListView.as_view(), name='orden_lista'),
    path('nueva/', views.OrdenServicioCreateView.as_view(), name='orden_crear'),
    path('<int:pk>/', views.OrdenServicioDetailView.as_view(), name='orden_detalle'),
    path('<int:pk>/editar/', views.OrdenServicioUpdateView.as_view(), name='orden_editar'),
    path('<int:pk>/seguimiento/', views.agregar_seguimiento, name='agregar_seguimiento'),
    path('<int:pk>/estado/', views.cambiar_estado, name='cambiar_estado'),
    path('<int:pk>/entrega/', views.registrar_entrega, name='registrar_entrega'),
    path('<int:pk>/anticipo/', views.registrar_anticipo, name='registrar_anticipo'),
    path('<int:pk>/constancia.pdf', views.constancia_recepcion_pdf, name='constancia_pdf'),
    path('<int:orden_pk>/cotizaciones/nueva/', views.crear_cotizacion, name='cotizacion_crear'),
    path('cotizaciones/<int:pk>/', views.CotizacionServicioDetailView.as_view(), name='cotizacion_detalle'),
    path('cotizaciones/<int:pk>/editar/', views.editar_cotizacion, name='cotizacion_editar'),
    path('cotizaciones/<int:pk>/pdf/', views.cotizacion_pdf, name='cotizacion_pdf'),
    path('cotizaciones/<int:pk>/<str:decision>/', views.decidir_cotizacion, name='cotizacion_decidir'),
]
