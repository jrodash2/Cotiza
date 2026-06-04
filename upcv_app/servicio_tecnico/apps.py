from django.apps import AppConfig


class ServicioTecnicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'servicio_tecnico'
    verbose_name = 'Servicio técnico'

    def ready(self):
        from . import signals  # noqa: F401
