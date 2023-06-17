from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError


class BaseModel(models.Model):
    objects = models.Manager()

    class Meta:
        abstract = True


class MoneyAccount(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    starting_balance = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} (balance: {self.balance})"

    class Meta:
        verbose_name_plural = "MoneyAccounts"


class BalanceHistory(models.Model):
    money_account = models.ForeignKey(MoneyAccount, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "BalanceHistories"
        ordering = ['timestamp']


class MainCategory(BaseModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "MainCategories"
        ordering = ["name"]


class SubCategory(BaseModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "SubCategories"
        ordering = ["name"]


class Category(BaseModel):
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE)
    TRANSFER_CHOICES = [
        ('INNER', 'INNER'),
        ('INCOMING', 'INCOMING'),
        ('OUTGOING', 'OUTGOING'),
    ]
    transaction_type = models.CharField(max_length=255, choices=TRANSFER_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.main_category.name} - {self.subcategory.name}"

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = [['main_category', 'subcategory']]
        ordering = ['main_category', 'subcategory']


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
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    # created_at = models.DateTimeField(null=True, blank=True)
    # updated_at = models.DateTimeField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    origin = models.CharField(max_length=255, choices=ORIGIN_CHOICES)
    destination = models.CharField(max_length=255, choices=ORIGIN_CHOICES)
    year = models.PositiveIntegerField(blank=True, null=True)
    transaction_type = models.CharField(max_length=255, choices=TRANSFER_CHOICES, blank=True, null=True)
    description = models.CharField(max_length=255, null=True)

    def save(self, *args, **kwargs):
        if self.category:
            self.main_category = self.category.main_category
            self.subcategory = self.category.subcategory

        if self.pk is not None:
            # Get the previous amount before updating
            previous_entry = BudgetExpenseEntry.objects.get(pk=self.pk)
            previous_amount = previous_entry.amount
            # Get the previous origin and destination
            previous_origin = previous_entry.origin
            previous_destination = previous_entry.destination
        else:
            previous_origin = ''
            previous_destination = ''
            previous_amount = 0

        def update_account(account_name, amount):
            account = MoneyAccount.objects.get(name=account_name)
            account.balance += amount
            account.save()

        # rollback existing changes
        if self.pk is not None:
            if previous_origin != 'OUT':
                update_account(previous_origin, previous_amount)
            if previous_destination != 'OUT':
                update_account(previous_destination, -previous_amount)
            # if roll back was done then balance will have the previous amount already subtracted from it, so the new amount will be distributed accordingly
            previous_amount = 0

        if self.origin == 'OUT':
            # Transfer from outside, increase amount on destination account
            update_account(self.destination, self.amount - previous_amount)  # add the difference of amounts +(105 - 100) = +5, or +105 if +100 already rolled back
            self.transaction_type = 'INCOMING'
        elif self.destination == 'OUT':
            # Transfer to outside, decrease amount on origin account
            update_account(self.origin, -(self.amount - previous_amount))  # subtract the difference of amounts -(105 - 100) = -5, or -105 if -100 already rolled back
            self.transaction_type = 'OUTGOING'
        else:
            # Transfer between accounts, adjust origin and destination balances
            update_account(self.origin, -(self.amount - previous_amount))
            update_account(self.destination, self.amount - previous_amount)
            self.transaction_type = 'INNER'

        self.year = self.date.year

        def update_balance_history(account_name):
            money_account = MoneyAccount.objects.get(name=account_name)
            balance_history = BalanceHistory(money_account=money_account, balance=money_account.balance)
            balance_history.save()

        # Update the balance history for MoneyAccounts
        if self.origin in ["CASH", "PKO", "ING"]:
            update_balance_history(self.origin)
        if self.destination in ["CASH", "PKO", "ING"]:
            update_balance_history(self.destination)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.origin != 'OUT':
            # Transfer to outside, increase amount on origin account
            origin_account = MoneyAccount.objects.get(name=self.origin)
            origin_account.balance += self.amount
            origin_account.save()
        if self.destination != 'OUT':
            # Transfer from outside, decrease amount on destination account
            destination_account = MoneyAccount.objects.get(name=self.destination)
            destination_account.balance -= self.amount
            destination_account.save()

        super().delete(*args, **kwargs)

    def clean(self):
        if self.origin == self.destination:
            raise ValidationError("Origin and destination cannot be the same.")

    def __str__(self):
        return f"{self.date} - {self.category}: {self.amount}"

    class Meta:
        verbose_name_plural = "BudgetEntries"
