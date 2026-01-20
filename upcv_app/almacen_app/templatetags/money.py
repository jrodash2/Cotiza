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
