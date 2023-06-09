from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
from calendar import month_name


def create_summary_table(year):
    # Get all main categories
    main_categories = MainCategory.objects.all()

    # Create a dictionary to store the summary data
    summary_table = {}

    # Initialize a dictionary to store the monthly totals across all subcategories
    monthly_totals = {}

    # Initialize a dictionary to store the category totals across all subcategories and months
    category_totals = {}

    # Loop through each main category
    for main_category in main_categories:
        # Get all subcategories for the current main category
        subcategories = SubCategory.objects.filter(category__main_category=main_category)
        # Create a list to store the row data for the current main category
        main_category_data = []

        # Initialize variables for total amounts
        category_total = 0
        subcategory_totals = {}

        # Initialize a dictionary to store the monthly totals per category across all subcategories
        category_monthly_totals = {}

        # Loop through each subcategory
        for subcategory in subcategories:
            # Query the BudgetExpenseEntry model to get the monthly summary for the given year
            monthly_summary = BudgetExpenseEntry.objects.filter(
                category__main_category=main_category,
                category__subcategory=subcategory,
                year=year,
                transaction_type__in=['INNER', 'OUTGOING']  # Filter for INNER and OUTGOING transactions
            ).values('date__month').annotate(total_amount=Sum('amount'))

            total_for_sub = 0

            # Create a dictionary to store the monthly summary for the subcategory
            subcategory_summary = {}
            # Loop through the monthly summary data
            for entry in monthly_summary:
                month = month_name[entry['date__month']]
                total_amount = entry['total_amount']
                subcategory_summary[month] = total_amount

                # Update subcategory total
                if subcategory in subcategory_totals:
                    subcategory_totals[subcategory] += total_amount
                else:
                    subcategory_totals[subcategory] = total_amount

                # Update category total
                category_total += total_amount
                total_for_sub += total_amount

                # Update monthly totals across all subcategories
                if month in monthly_totals:
                    monthly_totals[month] += total_amount
                else:
                    monthly_totals[month] = total_amount

                # Update monthly totals per category across all subcategories
                if month in category_monthly_totals:
                    category_monthly_totals[month] += total_amount
                else:
                    category_monthly_totals[month] = total_amount

            subcategory_summary["Total_for_sub"] = total_for_sub

            # Append the subcategory summary to the main category data list
            main_category_data.append({
                'subcategory': subcategory.name,
                'summary': subcategory_summary
            })

        main_category_data.append({
            'total_per_month': category_monthly_totals
        })

        # Add the main category data to the summary table dictionary
        summary_table[main_category.name] = main_category_data

        # Add the category total to the category_totals dictionary
        category_totals[main_category.name] = category_total

    return summary_table, category_totals


class BaseModel(models.Model):
    objects = models.Manager()

    class Meta:
        abstract = True


class MoneyAccount(BaseModel):
    name = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} (balance: {self.balance})"

    class Meta:
        verbose_name_plural = "MoneyAccounts"


class MainCategory(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "MainCategories"


class SubCategory(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "SubCategories"


class Category(BaseModel):
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.main_category.name} - {self.subcategory.name}"

    class Meta:
        verbose_name_plural = "Categories"


class BudgetExpenseEntry(BaseModel):
    ORIGIN_CHOICES = [
        ('ING', 'ING'),
        ('PKO', 'PKO'),
        ('CASH', 'CASH'),
        ('OUT', 'OUT'),
    ]
    TRANSFER_CHOICES = [
        ('INNER', 'INNER'),
        ('INCOMING', 'INCOMING'),
        ('OUTGOING', 'OUTGOING'),
    ]

    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    origin = models.CharField(max_length=255, choices=ORIGIN_CHOICES)
    destination = models.CharField(max_length=255, choices=ORIGIN_CHOICES)
    year = models.PositiveIntegerField(blank=True, null=True)
    transaction_type = models.CharField(max_length=255, choices=TRANSFER_CHOICES, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.category:
            self.main_category = self.category.main_category
            self.subcategory = self.category.subcategory

        if self.pk is not None:
            # Get the previous amount before updating
            previous_entry = BudgetExpenseEntry.objects.get(pk=self.pk)
            previous_amount = previous_entry.amount
        else:
            previous_amount = 0

        if self.origin == 'OUT':
            # Transfer from outside, increase amount on destination account
            destination_account = MoneyAccount.objects.get(name=self.destination)
            destination_account.balance += (self.amount - previous_amount)
            destination_account.save()
            self.transaction_type = 'INCOMING'
        elif self.destination == 'OUT':
            # Transfer to outside, decrease amount on origin account
            origin_account = MoneyAccount.objects.get(name=self.origin)
            origin_account.balance -= (self.amount - previous_amount)
            origin_account.save()
            self.transaction_type = 'OUTGOING'
        else:
            # Transfer between accounts, adjust origin and destination balances
            origin_account = MoneyAccount.objects.get(name=self.origin)
            destination_account = MoneyAccount.objects.get(name=self.destination)
            origin_account.balance -= (self.amount - previous_amount)
            destination_account.balance += (self.amount - previous_amount)
            origin_account.save()
            destination_account.save()
            self.transaction_type = 'INNER'

        self.year = self.date.year
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        origin_account = MoneyAccount.objects.get(name=self.origin)
        destination_account = MoneyAccount.objects.get(name=self.destination)

        if self.origin == 'OUT':
            # Transfer from outside, decrease amount on destination account
            destination_account.balance -= self.amount
        elif self.destination == 'OUT':
            # Transfer to outside, increase amount on origin account
            origin_account.balance += self.amount
        else:
            # Transfer between accounts, adjust origin and destination balances
            origin_account.balance += self.amount
            destination_account.balance -= self.amount

        origin_account.save()
        destination_account.save()

        super().delete(*args, **kwargs)

    def clean(self):
        if self.origin == self.destination:
            raise ValidationError("Origin and destination cannot be the same.")

    def __str__(self):
        return f"{self.date} - {self.category}: {self.amount}"

    class Meta:
        verbose_name_plural = "BudgetEntries"
