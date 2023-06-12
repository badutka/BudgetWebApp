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
