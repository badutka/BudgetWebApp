from django.urls import path

from .views import (
    transactions_list_view,
    transaction_add,
    transaction,
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
    TransactionsAPIView,
    TransactionAPIView,
    TransactionFormAPIView,
    ChartDataAPIView,
    BalanceHistoryRefreshAPIView,
)

from rest_framework import permissions
from drf_yasg.views import get_schema_view
# from rest_framework.schemas import get_schema_view  # openAPI  # https://www.django-rest-framework.org/api-guide/schemas/
# from rest_framework_swagger.views import get_swagger_view  # django-rest-swagger
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Your API Title",
        default_version='v1',
        description="Your API description",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # 1. Get Transactions
    path('transactions/', transactions_list_view, name='transactions'),
    # 2. Create a new Transaction
    path('transactions/add/', transaction_add, name='transaction_add'),
    # 3. Get Transaction
    path('transactions/<int:transaction_id>/', transaction, name='transaction'),
    # 4. Update the Transaction
    path('transactions/<int:transaction_id>/edit/', transaction_edit, name='transaction_edit'),
    # 5. Delete the Transaction
    path('transactions/<int:transaction_id>/delete/', transaction_delete, name='transaction_delete'),
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
    # 1. Get Transactions
    path('api/transactions/', TransactionsAPIView.as_view(), name='transactions_api'),
    # 2. Create a new Transaction
    path('api/transactions/', TransactionsAPIView.as_view(), name='transaction_add_api'),
    # 3. Get Transaction
    path('api/transactions/<int:transaction_id>/', TransactionAPIView.as_view(), name='transaction_api'),
    # 4. Update the Transaction
    path('api/transactions/<int:transaction_id>/', TransactionAPIView.as_view(), name='transaction_update_api'),
    # 5. Delete the Transaction
    path('api/transactions/<int:transaction_id>/', TransactionAPIView.as_view(), name='transaction_delete_api'),
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

    # 4.2. Edit Transaction Form
    # path('api/transactions/form/<int:transaction_id>/', TransactionFormAPIView.as_view(), name='transaction_form_api'),  # todo: create a separate, better suited form

    # API DOCS
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='api_docs'),
    # path('openapi', get_schema_view(title="Your Project", description="API for all things …"), name='openapi-schema'),
    # path('api/docs/', get_swagger_view(title='Your API Title')),
    # path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
