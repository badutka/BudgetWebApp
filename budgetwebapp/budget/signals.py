from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import BalanceHistory

# @receiver(pre_delete, sender=BudgetExpenseEntry)
# def delete_balance_history(sender, instance, **kwargs):
#     # Delete associated BalanceHistory record
#     try:
#         balance_history = instance.balancehistory
#         balance_history.delete()
#     except BalanceHistory.DoesNotExist:
#         pass

from django.db.models.signals import post_delete

# @receiver(post_delete, sender=BudgetExpenseEntry)
# def delete_balance_history(sender, instance, **kwargs):
#     entry_id = instance.id
#     balance_history = BalanceHistory.objects.get(budget_entry_id=entry_id)
#     balance_history.delete()


# post_delete.connect(delete_balance_history, sender=BudgetExpenseEntry)
