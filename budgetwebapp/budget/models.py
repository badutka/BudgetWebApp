from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from rest_framework import serializers


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


class ParentCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "ParentCategories"
        ordering = ["name"]


class Category(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    parent_category = models.ForeignKey(ParentCategory, on_delete=models.CASCADE)

    TRANSFER_CHOICES = [
        ('INNER', 'INNER'),
        ('INCOMING', 'INCOMING'),
        ('OUTGOING', 'OUTGOING'),
    ]
    transaction_type = models.CharField(max_length=255, choices=TRANSFER_CHOICES)

    def __str__(self):
        # return f"{self.parent_category.name} - {self.name} ({self.transaction_type})"
        return f"{self.parent_category.name} - {self.name}"

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = [['parent_category', 'name']]
        ordering = ['parent_category', 'name']


class Transaction(BaseModel):
    TRANSACTION_TYPE_CHOICES = [
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
    origin = models.ForeignKey(MoneyAccount, on_delete=models.SET_NULL, related_name='transactions_origin', null=True,
                               blank=True)
    destination = models.ForeignKey(MoneyAccount, on_delete=models.SET_NULL, related_name='transactions_destination',
                                    null=True, blank=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    transaction_type = models.CharField(max_length=255, choices=TRANSACTION_TYPE_CHOICES, blank=True, null=True)
    description = models.CharField(max_length=255, null=True)

    def save(self, *args, **kwargs):
        # Auto-determine transaction type
        if self.origin and self.destination:
            self.transaction_type = 'INNER'
        elif self.origin and not self.destination:
            self.transaction_type = 'OUTGOING'
        elif not self.origin and self.destination:
            self.transaction_type = 'INCOMING'
        else:
            raise ValidationError("Either origin or destination must be set.")

        self.year = self.date.year

        # Update MoneyAccount balances
        def update_account(account, amount):
            if account:
                account.balance += amount
                account.save()

        if self.pk:  # Update case
            previous = Transaction.objects.get(pk=self.pk)

            update_account(previous.origin, previous.amount)
            update_account(previous.destination, -previous.amount)

            # origin / destination could have been updated, so refresh
            if self.origin:
                self.origin = MoneyAccount.objects.get(pk=self.origin.pk)
            if self.destination:
                self.destination = MoneyAccount.objects.get(pk=self.destination.pk)

        update_account(self.origin, -self.amount)
        update_account(self.destination, self.amount)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.origin is not None:
            # Transfer to outside, increase amount on origin account
            self.origin.balance += self.amount
            self.origin.save()

        if self.destination is not None:
            # Transfer from outside, decrease amount on destination account
            self.destination.balance -= self.amount
            self.destination.save()

        super().delete(*args, **kwargs)

    def clean(self):
        if not self.origin and not self.destination:
            raise ValidationError("At least one of origin or destination must be set[transaction_clean].")

        if self.origin and self.destination and self.origin == self.destination:
            raise ValidationError("Origin and destination cannot be the same MoneyAccount[transaction_clean].")

    def __str__(self):
        return f"{self.date} - {self.category}: {self.amount}"

    class Meta:
        verbose_name_plural = "Transactions"
        ordering = ['-date', '-updated_at', '-id']


class BalanceHistory(models.Model):
    money_account = models.ForeignKey(MoneyAccount, on_delete=models.CASCADE)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(null=True, blank=True)  # , editable=False
    budget_entry = models.ForeignKey(Transaction, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "BalanceHistories"
        ordering = ['-budget_entry__date', '-budget_entry__updated_at', '-id']
