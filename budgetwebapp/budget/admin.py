from django.contrib import admin
from .models import MoneyAccount, Transaction, Category, MainCategory, SubCategory, BalanceHistory

admin.site.register(MoneyAccount)
admin.site.register(Transaction)
admin.site.register(Category)
admin.site.register(MainCategory)
admin.site.register(SubCategory)
admin.site.register(BalanceHistory)
