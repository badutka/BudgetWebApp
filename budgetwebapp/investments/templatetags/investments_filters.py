from django import template
from investments.models import Account

register = template.Library()

@register.filter
def account_by_type(account_type):
    return Account.objects.filter(type=account_type).first()