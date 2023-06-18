from decimal import Decimal, ROUND_DOWN
from django.core.management.base import BaseCommand
from django.utils import timezone

import pandas as pd
from datetime import datetime, time
from budget.models import Transaction

from budget.models import SubCategory, MainCategory, Category, MoneyAccount, Transaction


def level_accounts_balances():
    accs = MoneyAccount.objects.all()
    for acc in accs:
        acc.balance = acc.starting_balance
        acc.save()


def remove_all_budget_entries():
    Transaction.objects.all().delete()


def get_or_create_category(main_category_name, subcategory_name, origin, destination):
    try:
        # Try to get the existing Category object based on the provided names
        category = Category.objects.get(subcategory__name=subcategory_name, main_category__name=main_category_name)
        print(f"Retrieved existing category by name: '{category}'.")
    except Category.DoesNotExist:
        # If the Category doesn't exist, create a new one along with MainCategory and Subcategory
        subcategory, was_created = SubCategory.objects.get_or_create(name=subcategory_name)

        if was_created:
            print(f"Created new subcategory: '{subcategory}'.")
        else:
            print(f"Retrieved subcategory by name: '{subcategory}'.")

        # Get or create the MainCategory object
        main_category, was_created = MainCategory.objects.get_or_create(name=main_category_name)

        if was_created:
            print(f"Created new main category: '{main_category}'.")
        else:
            print(f"Retrieved main category by name: '{main_category}'.")

        if origin == 'OUT':
            transaction_type = "INCOMING"
        elif destination == 'OUT':
            transaction_type = "OUTGOING"
        else:
            transaction_type = "INNER"

        # Create the new Category object
        category = Category.objects.create(
            subcategory=subcategory,
            main_category=main_category,
            transaction_type=transaction_type
        )

        print(f"Created new category: '{category}'.")

    return category


def populate_budget_entries(excel_file_path):
    # Disable auto_now_add and auto_now
    created_at_field = Transaction._meta.get_field('created_at')
    created_at_field.auto_now_add = False
    updated_at_field = Transaction._meta.get_field('updated_at')
    updated_at_field.auto_now = False

    remove_all_budget_entries()
    level_accounts_balances()

    # Read the Excel file using pandas
    df = pd.read_excel(excel_file_path)

    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        # Extract the data from the row
        date = row['Date'].strftime('%Y-%m-%d')
        created_at = row['Created at']
        updated_at = row['Updated at']
        category_name = row['Category']
        main_category_name = category_name.split(' - ')[0]
        subcategory_name = category_name.split(' - ')[1]
        amount = Decimal(str(row['Amount']))
        origin = row['Origin']
        destination = row['Destination']
        description = row['Description']

        category = get_or_create_category(main_category_name, subcategory_name, origin, destination)

        # # Create a BudgetExpenseEntry object
        entry = Transaction()
        entry.date = datetime.strptime(date, '%Y-%m-%d').date()

        if created_at is not None:
            entry.created_at = timezone.make_aware(created_at)
        else:
            entry.created_at = timezone.make_aware(datetime.combine(entry.date, time(12, 0)))

        if updated_at is not None:
            entry.updated_at = timezone.make_aware(updated_at)
        else:
            entry.updated_at = timezone.make_aware(datetime.combine(entry.date, time(12, 0)))

        entry.category = category
        entry.amount = amount
        entry.origin = origin
        entry.destination = destination
        entry.description = description

        # Save the entry to the database
        entry.save()

        print(f"Created new expense entry: {{Date: {entry.date}, Category: {entry.category}, Amount: {entry.amount}, Origin: {entry.origin}, Destination: {entry.destination}}}.\n{10 * '-'}")
    print(f"\nPopulated {len(df)} records.\n")

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
