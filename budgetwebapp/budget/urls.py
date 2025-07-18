from django.urls import path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
# from rest_framework.schemas import get_schema_view  # openAPI  # https://www.django-rest-framework.org/api-guide/schemas/
# from rest_framework_swagger.views import get_swagger_view  # django-rest-swagger
from drf_yasg import openapi

import budget.views as budget_views
import api.views as api_views

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
    # Home (default)
    path('', budget_views.transactions_list_view, name='transactions'),
    # Get Transactions
    path('transactions/', budget_views.transactions_list_view, name='transactions'),
    # Create a new Transaction
    path('transactions/add/', budget_views.transaction_add, name='transaction_add'),
    # Get Transaction
    path('transactions/<int:transaction_id>/', budget_views.transaction, name='transaction'),
    # Update the Transaction
    path('transactions/<int:transaction_id>/edit/', budget_views.transaction_edit, name='transaction_edit'),
    # Delete the Transaction
    path('transactions/<int:transaction_id>/delete/', budget_views.transaction_delete, name='transaction_delete'),
    # Duplicate Transaction
    path('transactions/<int:transaction_id>/duplicate/', budget_views.duplicate_transaction, name='duplicate_transaction'),
    # Get Detailed Summaries
    path('transactions/monthly-summary-detailed/', budget_views.monthly_summary_detailed_view, name='monthly_summary_detailed'),
    # Get Summaries
    path('transactions/monthly-summary/', budget_views.monthly_summary_view, name='monthly_summary'),
    # Charts View
    path('transactions/chart-summary/', budget_views.chart_summary, name='chart_summary'),
    # Balance History View
    path('balance-history/<str:money_account_name>/', budget_views.balance_history_view, name='balance_history'),
    # Balance History Refresh
    path('balance-history/refresh/<str:money_account_name>/', budget_views.refresh_balance_history, name='balance_history_refresh'),
]

urlpatterns = urlpatterns + [
    # Get Transactions
    path('api/transactions/', api_views.TransactionsAPIView.as_view(), name='transactions_api'),
    # Create a new Transaction
    path('api/transactions/', api_views.TransactionsAPIView.as_view(), name='transaction_add_api'),
    # Get Transaction
    path('api/transactions/<int:transaction_id>/', api_views.TransactionAPIView.as_view(), name='transaction_api'),
    # Update the Transaction
    path('api/transactions/<int:transaction_id>/', api_views.TransactionAPIView.as_view(), name='transaction_update_api'),
    # Delete the Transaction
    path('api/transactions/<int:transaction_id>/', api_views.TransactionAPIView.as_view(), name='transaction_delete_api'),
    # Duplicate Transaction
    path('api/transactions/<int:transaction_id>/duplicate/', api_views.TransactionDuplicateAPIView.as_view(), name='transaction_duplicate_api'),
    # Get Money Accounts
    path('api/money-accounts/', api_views.MoneyAccountAPIView.as_view(), name='money_accounts'),
    # Get Summaries
    path('api/monthly-summaries/', api_views.MonthlySummaryAPIView.as_view(), name='monthly_summaries'),
    # Get Summary
    path('api/monthly-summaries/<int:year>/<int:month>/', api_views.MonthlySummaryAPIView.as_view(), name='monthly_summaries'),
    # Get Category Summaries
    path('api/monthly-category-summaries/', api_views.MonthlyCategorySummaryAPIView.as_view(), name='monthly_category_summaries'),
    # Get Parent Category Summaries
    path('api/monthly-parent-category-summaries/', api_views.MonthlyParentCategorySummaryAPIView.as_view(), name='monthly_parent_category_summaries'),
    # Get Parent Categories
    path('api/parent-categories/', api_views.ParentCategoryAPIView.as_view(), name='parent_categories'),
    # Charts view
    path('api/chart-data/', api_views.ChartDataAPIView.as_view(), name='chart-data'),
    # Balance History View
    path('api/balance-history/<str:money_account_name>/', api_views.BalanceHistoryAPIView.as_view(), name='balance-history-api'),
    # Balance History Refresh
    path('api/balance-history/refresh/<str:money_account_name>/', api_views.BalanceHistoryRefreshAPIView.as_view(), name='balance-history-refresh-api'),
    # Edit Transaction Form
    # path('api/transactions/form/<int:transaction_id>/', TransactionFormAPIView.as_view(), name='transaction_form_api'),  # todo: create a separate, better suited form

    # API DOCS
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='api_docs'),
    # path('openapi', get_schema_view(title="Your Project", description="API for all things …"), name='openapi-schema'),
    # path('api/docs/', get_swagger_view(title='Your API Title')),
    # path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
