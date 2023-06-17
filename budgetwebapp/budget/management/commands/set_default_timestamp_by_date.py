from datetime import datetime, time
from django.utils.timezone import make_aware
from django.core.management.base import BaseCommand
from budget.models import BudgetExpenseEntry

class Command(BaseCommand):
    help = 'Update timestamps for BudgetExpenseEntry records without a timestamp'

    def handle(self, *args, **options):
        # entries_without_timestamp = BudgetExpenseEntry.objects.filter(created_at__isnull=True)
        entries_without_timestamp = BudgetExpenseEntry.objects.all()

        for entry in entries_without_timestamp:
            # entry.timestamp = datetime.combine(entry.date, time(12, 0))
            # entry.created_at = make_aware(entry.date.replace(hour=12, minute=0))
            entry.created_at = make_aware(datetime.combine(entry.date, time(12, 0)))
            entry.updated_at = make_aware(datetime.combine(entry.date, time(12, 0)))
            entry.save()

        self.stdout.write(self.style.SUCCESS('Timestamps updated successfully.'))