from django.urls import path
from .views import (
    budget_expense_entry_list,
    budget_entry_add,
    budget_entry_edit,
    budget_entry_remove,
    incoming_transaction_list_view,
    outgoing_transaction_list_view,
    monthly_expense_summary_view,
    monthly_income_summary_view,
    yearly_expense_summary_view,
    chart_summary,
    ChartDataAPIView,
)

urlpatterns = [
    path('', budget_expense_entry_list, name='budget_expense_entry_list'),
    path('add/', budget_entry_add, name='budget_entry_add'),
    path('edit/<int:entry_id>/', budget_entry_edit, name='budget_entry_edit'),
    path('remove/<int:entry_id>/', budget_entry_remove, name='budget_entry_remove'),
    path('transactions/incoming/', incoming_transaction_list_view, name='incoming_transactions'),
    path('transactions/outgoing/', outgoing_transaction_list_view, name='outgoing_transactions'),
    path('transactions/monthly-expense-summary/', monthly_expense_summary_view, name='monthly_expense_summary'),
    path('transactions/monthly-income-summary/', monthly_income_summary_view, name='monthly_income_summary'),
    path('transactions/yearly-expense-summary/', yearly_expense_summary_view, name='yearly_expense_summary'),
    path('transactions/chart-summary/', chart_summary, name='chart_summary'),
    path('api/chart-data/', ChartDataAPIView.as_view(), name='chart-data'),
    # path('transactions/outgoing/', OutgoingTransactionListView.as_view(), name='outgoing_transactions'),
]