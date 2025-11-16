from django import template
from investments.models import Account

register = template.Library()


@register.filter
def real_widget(widget):
    """
    Returns the most-derived instance of a widget (handles multi-table inheritance).
    """
    if not widget:
        return None
    if hasattr(widget, "get_real_instance"):
        return widget.get_real_instance()
    return widget


@register.filter
def account_by_type(account_type):
    return Account.objects.filter(type=account_type).first()


@register.filter
def addstr(arg1, arg2):
    """concatenate arg1 & arg2"""
    return str(arg1) + str(arg2)
