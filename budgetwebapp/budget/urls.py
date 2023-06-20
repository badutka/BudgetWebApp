from django.urls import path
from .views import (
    transactions_list_view,
    transaction_add,
    transaction_edit,
    transaction_remove,
    incoming_transactions_list_view,
    outgoing_transactions_list_view,
    monthly_expense_summary_view,
    monthly_income_summary_view,
    yearly_expense_summary_view,
    chart_summary,
    ChartDataAPIView,
    BalanceHistoryAPIView,
    balance_history_view
    # ChartSummaryView,

)

urlpatterns = [
    path('', transactions_list_view, name='transactions'),
    path('add/', transaction_add, name='transaction_add'),
    path('edit/<int:transaction_id>/', transaction_edit, name='transaction_edit'),
    path('remove/<int:transaction_id>/', transaction_remove, name='transaction_remove'),
    path('transactions/incoming/', incoming_transactions_list_view, name='incoming_transactions'),
    path('transactions/outgoing/', outgoing_transactions_list_view, name='outgoing_transactions'),
    path('transactions/monthly-expense-summary/', monthly_expense_summary_view, name='monthly_expense_summary'),
    path('transactions/monthly-income-summary/', monthly_income_summary_view, name='monthly_income_summary'),
    path('transactions/yearly-expense-summary/', yearly_expense_summary_view, name='yearly_expense_summary'),
    path('transactions/chart-summary/', chart_summary, name='chart_summary'),
    # path('transactions/chart-summary/', ChartSummaryView.as_view(), name='chart_summary'),
    path('api/chart-data/', ChartDataAPIView.as_view(), name='chart-data'),
    path('balance-history/<str:money_account_name>/', balance_history_view, name='balance_history'),
    path('api/balance-history/<str:money_account_name>/', BalanceHistoryAPIView.as_view(), name='balance-history-api'),
]