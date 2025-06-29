from decimal import Decimal, ROUND_DOWN
from django.core.management.base import BaseCommand
from django.utils import timezone

import pandas as pd
from datetime import datetime, time, timedelta
from budget.models import Transaction

from budget.models import Category, ParentCategory, MoneyAccount, Transaction


def level_accounts_balances():
    accs = MoneyAccount.objects.all()
    for acc in accs:
        acc.balance = acc.starting_balance
        acc.save()


def remove_all_budget_entries():
    Transaction.objects.all().delete()


def get_or_create_category(category_name, origin, destination):
    if origin is None:
        transaction_type = "INCOMING"
    elif destination is None:
        transaction_type = "OUTGOING"
    else:
        transaction_type = "INNER"

    pc = ParentCategory.objects.get(name='Other')

    # Create the new Category object
    category, was_created = Category.objects.get_or_create(
        name=category_name,
        parent_category=pc,
        transaction_type=transaction_type
    )

    if was_created:
        print(f"Created new subcategory: '{category_name}'.")
    else:
        print(f"Retrieved subcategory by name: '{category_name}'.")

    return category


def populate_budget_entries(excel_file_path):
    # Disable auto_now_add and auto_now
    created_at_field = Transaction._meta.get_field('created_at')
    created_at_field.auto_now_add = False
    updated_at_field = Transaction._meta.get_field('updated_at')
    updated_at_field.auto_now = False

    remove_all_budget_entries()
    level_accounts_balances()
    #
    # # Read the Excel file using pandas
    df = pd.read_excel(excel_file_path, skiprows=5)
    df = df[['Date', 'Category', 'Expense', 'Income']]

    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        # Extract the data from the row
        date = row['Date'] + timedelta(hours=12)
        created_at = date
        updated_at = date
        category_name = row['Category']
        amount = row['Expense'] if row['Expense'] >= 0 else row['Income']
        amount = Decimal(amount)
        origin = 'ING'
        destination = ''
        description = ''

        entry = Transaction()
        entry.date = date

        if created_at is not None:
            entry.created_at = timezone.make_aware(created_at)
        else:
            entry.created_at = timezone.make_aware(datetime.combine(entry.date, time(12, 0)))

        if updated_at is not None:
            entry.updated_at = timezone.make_aware(updated_at)
        else:
            entry.updated_at = timezone.make_aware(datetime.combine(entry.date, time(12, 0)))


        entry.amount = amount
        origin = MoneyAccount.objects.get(name=origin) if origin else None
        destination = MoneyAccount.objects.get(name=destination) if destination else None

        if row['Income'] > 0:
            origin, destination = destination, origin
        entry.origin = origin
        entry.destination = destination
        category = get_or_create_category(category_name, origin, destination)

        entry.category = category
        entry.description = description

        entry.save()

        # print(f"Created new expense entry: {{Date: {entry.date}, Category: {entry.category}, Amount: {entry.amount}, Origin: {entry.origin}, Destination: {entry.destination}}}.\n{10 * '-'}")
        # print(f"\nPopulated {len(df)} records.\n")

    # Re-enable auto_now_add and auto_now
    created_at_field.auto_now_add = True
    updated_at_field.auto_now = True


class Command(BaseCommand):
    help = 'Populate BudgetExpenseEntry data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file')

    def handle(self, *args, **options):
        excel_file_path = options['excel_file']
        populate_budget_entries(excel_file_path)
        self.stdout.write(self.style.SUCCESS('Budget entries populated successfully.'))
