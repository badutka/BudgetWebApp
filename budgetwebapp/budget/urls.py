from django.urls import path

from .views import (
    transactions_list_view,
    transaction_add,
    transaction_edit,
    transaction_delete,
    incoming_transactions_list_view,
    outgoing_transactions_list_view,
    monthly_expense_summary_view,
    monthly_income_summary_view,
    yearly_expense_summary_view,
    chart_summary,
    BalanceHistoryAPIView,
    balance_history_view,
    duplicate_transaction,
    refresh_balance_history,
)

from api.views import (
    TransactionCreateAPIView,
    TransactionUpdateAPIView,
    TransactionFormAPIView,
    TransactionRemoveAPIView,
    ChartDataAPIView,
    BalanceHistoryRefreshAPIView,
)

urlpatterns = [
    # 1. Transactions List
    path('transactions', transactions_list_view, name='transactions'),
    # 2. Single Transaction

    # 3. Add Transaction
    path('transactions/add/', transaction_add, name='transaction_add'),
    # 4. Update Transaction
    path('transactions/<int:transaction_id>/', transaction_edit, name='transaction_edit'),
    # 5. Remove Transaction
    path('remove/<int:transaction_id>/', transaction_delete, name='transaction_delete'),
    # 6. Duplicate Transaction
    path('transactions/duplicate/<int:transaction_id>/', duplicate_transaction, name='duplicate_transaction'),
    # 7. Incoming Transactions List
    path('transactions/incoming/', incoming_transactions_list_view, name='incoming_transactions'),
    # 8. Outgoing Transactions List
    path('transactions/outgoing/', outgoing_transactions_list_view, name='outgoing_transactions'),
    # 9. Monthly Expense Summary
    path('transactions/monthly-expense-summary/', monthly_expense_summary_view, name='monthly_expense_summary'),
    # 10. Monthly Income Summary
    path('transactions/monthly-income-summary/', monthly_income_summary_view, name='monthly_income_summary'),
    # 11. Yearly Summary
    path('transactions/yearly-expense-summary/', yearly_expense_summary_view, name='yearly_expense_summary'),
    # 12. Charts view
    path('transactions/chart-summary/', chart_summary, name='chart_summary'),
    # 13. Balance History View
    path('balance-history/<str:money_account_name>/', balance_history_view, name='balance_history'),
    # 14. Balance History Refresh
    path('balance-history/refresh/<str:money_account_name>/', refresh_balance_history, name='balance_history_refresh'),

]

urlpatterns = urlpatterns + [
    # 1. Transactions List

    # 2. Single Transaction

    # 3. Add Transaction
    path('api/transactions/add/', TransactionCreateAPIView.as_view(), name='transaction_add_api'),
    # 4. Update Transaction
    path('api/transactions/edit/<int:transaction_id>/', TransactionUpdateAPIView.as_view(), name='transaction_update_api'),
    # 4.2. Edit Transaction Form
    path('api/transactions/form/<int:transaction_id>/', TransactionFormAPIView.as_view(), name='transaction_form_api'),  # todo: create a separate, better suited form
    # 5. Remove Transaction
    path('api/transactions/remove/<int:transaction_id>/', TransactionRemoveAPIView.as_view(), name='transaction_delete_api'),
    # 6. Duplicate Transaction

    # 7. Incoming Transactions List

    # 8. Outgoing Transactions List

    # 9. Monthly Expense Summary

    # 10. Monthly Income Summary

    # 11. Yearly Summary

    # 12. Charts view
    path('api/chart-data/', ChartDataAPIView.as_view(), name='chart-data'),
    # 13. Balance History View
    path('api/balance-history/<str:money_account_name>/', BalanceHistoryAPIView.as_view(), name='balance-history-api'),
    # 14. Balance History Refresh
    path('api/balance-history/refresh/<str:money_account_name>/', BalanceHistoryRefreshAPIView.as_view(), name='balance-history-refresh-api'),

]
