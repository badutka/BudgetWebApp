from django.contrib import admin
from .models import MoneyAccount, Transaction, ParentCategory, Category, BalanceHistory

admin.site.register(MoneyAccount)
admin.site.register(Transaction)
admin.site.register(Category)
admin.site.register(ParentCategory)
admin.site.register(BalanceHistory)
