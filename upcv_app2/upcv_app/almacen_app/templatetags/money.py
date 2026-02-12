from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter(name='money_q')
def money_q(value):
    if value in (None, ''):
        return 'Q0.00'
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return 'Q0.00'
    return f'Q{amount:,.2f}'


@register.filter(name='strip_http')
def strip_http(value):
    if not value:
        return ''
    text = str(value).strip()
    if text.startswith('http://'):
        return text[7:]
    if text.startswith('https://'):
        return text[8:]
    return text
