from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Transaction
from core.summaries.reporting import ReportsUtility, update_all_summaries


# @receiver(pre_delete, sender=BudgetExpenseEntry)
# def delete_balance_history(sender, instance, **kwargs):
#     # Delete associated BalanceHistory record
#     try:
#         balance_history = instance.balancehistory
#         balance_history.delete()
#     except BalanceHistory.DoesNotExist:
#         pass

# @receiver(post_delete, sender=BudgetExpenseEntry)
# def delete_balance_history(sender, instance, **kwargs):
#     entry_id = instance.id
#     balance_history = BalanceHistory.objects.get(budget_entry_id=entry_id)
#     balance_history.delete()

# post_delete.connect(delete_balance_history, sender=BudgetExpenseEntry)

# Store old date before save
@receiver(pre_save, sender=Transaction)
def cache_old_transaction_date(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        instance._old_year = old_instance.date.year
        instance._old_month = old_instance.date.month
    else:
        instance._old_year = None
        instance._old_month = None


# After save, update summaries
@receiver(post_save, sender=Transaction)
def update_summary_on_save(sender, instance, created, **kwargs):
    year = instance.date.year
    month = instance.date.month
    old_year = getattr(instance, '_old_year', None)
    old_month = getattr(instance, '_old_month', None)

    # Check if the year had any transactions *before* this one was saved
    is_first_transaction_in_year = ReportsUtility.is_new_transaction_year(year, created, instance)

    if old_year is not None and (old_year != year or old_month != month):
        # Date changed → update both months
        update_all_summaries(old_year, old_month)
        ReportsUtility.delete_summaries_if_year_empty(old_year)

    update_all_summaries(year, month)

    if is_first_transaction_in_year:
        for m in range(1, 13):
            if m != month:
                update_all_summaries(year, m)


# @receiver(post_delete, sender=Transaction)
# def update_summary_on_delete(sender, instance, **kwargs):
#     year = instance.date.year
#     month = instance.date.month
#     update_monthly_summary(year, month)
#     update_monthly_category_summary(year, month)
#     update_monthly_parent_category_summary(year, month)

# @receiver(post_save, sender=Transaction)
# def update_summary_on_save(sender, instance, **kwargs):
#     update_monthly_summary(instance.date.year, instance.date.month)

@receiver(post_delete, sender=Transaction)
def update_summary_on_delete(sender, instance, **kwargs):
    update_all_summaries(instance.date.year, instance.date.month)
    ReportsUtility.delete_summaries_if_year_empty(instance.date.year)
