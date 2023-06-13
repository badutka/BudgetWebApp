from decimal import Decimal, ROUND_DOWN
from django.core.management.base import BaseCommand

import pandas as pd
from datetime import datetime
from budget.models import BudgetExpenseEntry

from budget.models import SubCategory, MainCategory, Category


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
    # Read the Excel file using pandas
    df = pd.read_excel(excel_file_path)

    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        # Extract the data from the row
        date = row['Date'].strftime('%Y-%m-%d')
        category_name = row['Category']
        main_category_name = category_name.split(' - ')[0]
        subcategory_name = category_name.split(' - ')[1]
        amount = Decimal(str(row['Amount']))
        origin = row['Origin']
        destination = row['Destination']
        description = row['Description']

        category = get_or_create_category(main_category_name, subcategory_name, origin, destination)

        # Create a BudgetExpenseEntry object
        entry = BudgetExpenseEntry()
        entry.date = datetime.strptime(date, '%Y-%m-%d').date()
        entry.category = category  # You need to implement this utility function
        entry.amount = amount
        entry.origin = origin
        entry.destination = destination
        entry.description = description

        # Save the entry to the database
        entry.save()

        print(f"Created new expense entry: {{Date: {entry.date}, Category: {entry.category}, Amount: {entry.amount}, Origin: {entry.origin}, Destination: {entry.destination}}}.\n{10 * '-'}")
    print(f"\nPopulated {len(df)} records.\n")


class Command(BaseCommand):
    help = 'Populate BudgetExpenseEntry data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file')

    def handle(self, *args, **options):
        excel_file_path = options['excel_file']
        populate_budget_entries(excel_file_path)
        self.stdout.write(self.style.SUCCESS('Budget entries populated successfully.'))
