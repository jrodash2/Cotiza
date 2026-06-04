from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def configurar_roles_servicio(sender, **kwargs):
    if sender.name != 'servicio_tecnico':
        return
    permisos = Permission.objects.filter(content_type__app_label='servicio_tecnico')
    for nombre in ('Administrador', 'Recepcion', 'Tecnico', 'Técnico'):
        grupo, _ = Group.objects.get_or_create(name=nombre)
        if nombre == 'Administrador':
            grupo.permissions.add(*permisos)
        elif nombre == 'Recepcion':
            grupo.permissions.add(*permisos.exclude(codename='gestionar_tecnica'))
        else:
            grupo.permissions.add(*permisos.filter(codename__in=(
                'view_ordenservicio', 'change_ordenservicio', 'gestionar_tecnica',
                'add_seguimientoordenservicio', 'view_seguimientoordenservicio',
            )))
