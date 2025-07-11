from django.core.management.base import BaseCommand
from budget.models import Transaction  # adjust if your model is in a different app
from budget.reporting import update_all_summaries  # wherever your logic lives
from datetime import datetime

class Command(BaseCommand):
    help = 'Rebuild monthly summaries for entire years that have at least one transaction'

    def handle(self, *args, **kwargs):
        # Get all years that have transactions
        years_with_transactions = (
            Transaction.objects.dates('date', 'year', order='ASC')
            .distinct()
            .values_list('year', flat=True)
        )

        for year in years_with_transactions:
            self.stdout.write(f"Rebuilding summaries for year {year}...")
            for month in range(1, 13):
                update_all_summaries(year, month)

        self.stdout.write(self.style.SUCCESS("All yearly summaries updated."))