# management/commands/rebuild_non_zero_monthly_summaries.py
from django.core.management.base import BaseCommand
from core.summaries.reporting import update_all_summaries
from budgetwebapp.budget.models import Transaction


class Command(BaseCommand):
    help = 'Rebuild non-zero monthly summaries'

    def handle(self, *args, **kwargs):
        distinct_dates = Transaction.objects.dates('date', 'month', order='ASC')
        for dt in distinct_dates:
            year = dt.year
            month = dt.month
            update_all_summaries(year, month)
        self.stdout.write(self.style.SUCCESS("All non-zero summaries updated."))