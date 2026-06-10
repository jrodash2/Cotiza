def nombre_usuario(user):
    if not user:
        return ''

    get_full_name = getattr(user, 'get_full_name', None)
    if callable(get_full_name):
        full_name = get_full_name().strip()
        if full_name:
            return full_name

    first_name = getattr(user, 'first_name', '') or ''
    last_name = getattr(user, 'last_name', '') or ''
    fallback_name = f'{first_name} {last_name}'.strip()
    if fallback_name:
        return fallback_name

    username = getattr(user, 'username', '') or ''
    if username:
        return username
    return str(user)
