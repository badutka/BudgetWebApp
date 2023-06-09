from django.contrib import admin
from .models import MoneyAccount, BudgetExpenseEntry, Category, MainCategory, SubCategory

admin.site.register(MoneyAccount)
admin.site.register(BudgetExpenseEntry)
admin.site.register(Category)
admin.site.register(MainCategory)
admin.site.register(SubCategory)
