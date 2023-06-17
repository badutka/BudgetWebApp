import csv
from openpyxl import Workbook
from django.core.management.base import BaseCommand
from budget.models import BudgetExpenseEntry


class Command(BaseCommand):
    help = 'Export budget entries to CSV or XLSX file'

    def add_arguments(self, parser):
        parser.add_argument('output_file', type=str, help='Output file path')
        parser.add_argument('--format', choices=['csv', 'xlsx'], default='csv', help='Export format (csv or xlsx)')

    def handle(self, *args, **options):
        output_file = options['output_file']
        export_format = options['format']

        # Get all budget entries
        budget_entries = BudgetExpenseEntry.objects.all()

        self.export_to_file(output_file, budget_entries, export_format)

        self.stdout.write(self.style.SUCCESS(f'Successfully exported budget entries to {output_file} in {export_format.upper()} format'))

    def export_to_file(self, output_file, budget_entries, export_format):
        if export_format == 'csv':
            self.export_to_csv(output_file, budget_entries)
        elif export_format == 'xlsx':
            self.export_to_xlsx(output_file, budget_entries)

    def export_to_csv(self, output_file, budget_entries):
        # Prepare CSV data
        csv_data = self.prepare_data(budget_entries)

        # Write CSV data to file
        with open(output_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

    def export_to_xlsx(self, output_file, budget_entries):
        # Prepare data
        data = self.prepare_data(budget_entries)

        # Create a new workbook and get the active sheet
        workbook = Workbook()
        sheet = workbook.active

        # Write data to the sheet
        for row in data:
            sheet.append(row)

        # Save the workbook to the output file
        workbook.save(output_file)

    def prepare_data(self, budget_entries):
        # Prepare data
        data = [['Date', 'Created at', 'Updated at', 'Category', 'Amount', 'Origin', 'Destination', 'Year', 'Transaction Type', 'Description']]
        for entry in budget_entries:
            category = entry.category.main_category.name + ' - ' + entry.category.subcategory.name if entry.category.main_category and entry.category.subcategory else ''

            # Convert created_at and updated_at to timezone-aware datetimes with timezone set to None
            created_at = entry.created_at.replace(tzinfo=None) if entry.created_at else None
            updated_at = entry.updated_at.replace(tzinfo=None) if entry.updated_at else None

            data.append([
                entry.date,
                created_at,
                updated_at,
                category,
                entry.amount,
                entry.origin,
                entry.destination,
                entry.year,
                entry.transaction_type,
                entry.description,
            ])
        return data
