from django.contrib import admin
from .models import (MoneyAccount, Transaction, ParentCategory, Category, BalanceHistory,
                     MonthlySummary, MonthlyCategorySummary, MonthlyParentCategorySummary)

admin.site.register(MoneyAccount)
admin.site.register(Transaction)
admin.site.register(Category)
admin.site.register(ParentCategory)
admin.site.register(BalanceHistory)
admin.site.register(MonthlySummary)
admin.site.register(MonthlyCategorySummary)
admin.site.register(MonthlyParentCategorySummary)
