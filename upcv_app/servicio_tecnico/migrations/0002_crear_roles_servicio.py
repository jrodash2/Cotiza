from django.db import migrations


def crear_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    permisos = Permission.objects.filter(content_type__app_label='servicio_tecnico')
    for nombre in ('Administrador', 'Recepcion', 'Tecnico', 'Técnico'):
        grupo, _ = Group.objects.get_or_create(name=nombre)
        if nombre == 'Administrador':
            grupo.permissions.add(*permisos)
        elif nombre == 'Recepcion':
            grupo.permissions.add(*permisos.exclude(codename='gestionar_tecnica'))
        else:
            grupo.permissions.add(*permisos.filter(codename__in=('view_ordenservicio', 'change_ordenservicio', 'gestionar_tecnica', 'add_seguimientoordenservicio', 'view_seguimientoordenservicio')))


def eliminar_roles(apps, schema_editor):
    # No se eliminan grupos que podrían contener usuarios o existir previamente.
    pass


class Migration(migrations.Migration):
    dependencies = [('servicio_tecnico', '0001_initial')]
    operations = [migrations.RunPython(crear_roles, eliminar_roles)]
