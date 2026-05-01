from django.urls import path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
# from rest_framework.schemas import get_schema_view  # openAPI  # https://www.django-rest-framework.org/api-guide/schemas/
# from rest_framework_swagger.views import get_swagger_view  # django-rest-swagger
from drf_yasg import openapi

from budgetwebapp.budget.views import transactions_views, summary_views, dashboard_views, balance_history_views
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

# -------------------------
# Frontend Views (HTML)
# -------------------------
frontend_urls = [
    # Home & Transactions
    path('', transactions_views.transactions_list_view, name='transactions'),
    path('transactions/', transactions_views.transactions_list_view, name='transactions'),
    path('transactions/add/', transactions_views.transaction_add, name='transaction_add'),
    path('transactions/<int:transaction_id>/', transactions_views.transaction, name='transaction'),
    path('transactions/<int:transaction_id>/edit/', transactions_views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:transaction_id>/delete/', transactions_views.transaction_delete, name='transaction_delete'),
    path('transactions/<int:transaction_id>/duplicate/', transactions_views.duplicate_transaction, name='duplicate_transaction'),

    # Summaries
    path('transactions/monthly-summary-detailed/', summary_views.monthly_summary_detailed_view, name='monthly_summary_detailed'),
    path('transactions/monthly-summary/', summary_views.monthly_summary_view, name='monthly_summary'),

    # Charts
    path('transactions/chart-summary/', dashboard_views.chart_summary, name='chart_summary'),

    # Balance History
    path('balance-history/<str:money_account_name>/', balance_history_views.balance_history_view_new, name='balance_history'),
    path('balance-history/refresh/<str:money_account_name>/', balance_history_views.refresh_balance_history, name='balance_history_refresh'),

    # Category & Dashboard
    path('transactions/category/<int:category_id>/', transactions_views.transactions_by_category_modal, name='transactions_by_category'),
    path('dashboard/dashboard_card_modal', dashboard_views.dashboard_card_modal_view, name='dashboard_card_modal'),
]

# -------------------------
# API Endpoints (REST)
# -------------------------
api_urls = [
    # Transactions
    path('api/transactions/', api_views.TransactionsAPIView.as_view(), name='transactions_api'),
    path('api/transactions/<int:transaction_id>/', api_views.TransactionAPIView.as_view(), name='transaction_api'),
    path('api/transactions/<int:transaction_id>/duplicate/', api_views.TransactionDuplicateAPIView.as_view(), name='transaction_duplicate_api'),
    path('api/transactions/category/<int:category_id>/', api_views.TransactionsByCategoryAPIView.as_view(), name='api_transactions_by_category'),

    # Money Accounts
    path('api/money-accounts/', api_views.MoneyAccountAPIView.as_view(), name='money_accounts'),

    # Summaries
    path('api/monthly-summaries/', api_views.MonthlySummaryAPIView.as_view(), name='monthly_summaries'),
    path('api/monthly-summaries/<int:year>/<int:month>/', api_views.MonthlySummaryAPIView.as_view(), name='monthly_summaries'),
    path('api/monthly-category-summaries/', api_views.MonthlyCategorySummaryAPIView.as_view(), name='monthly_category_summaries'),
    path('api/monthly-parent-category-summaries/', api_views.MonthlyParentCategorySummaryAPIView.as_view(), name='monthly_parent_category_summaries'),

    # Categories
    path('api/parent-categories/', api_views.ParentCategoryAPIView.as_view(), name='parent_categories'),
    path('api/categories/', api_views.CategoryAPIView.as_view(), name='categories'),
    path('api/categories/<int:category_id>', api_views.CategoryAPIView.as_view(), name='categories'),

    # Charts
    path('api/chart-data/', api_views.ChartDataAPIView.as_view(), name='chart-data'),

    # Balance History
    path('api/balance-history/<str:money_account_name>/', api_views.BalanceHistoryAPIView.as_view(), name='balance-history-api'),
    path('api/balance-history/refresh/<str:money_account_name>/', api_views.BalanceHistoryRefreshAPIView.as_view(), name='balance-history-refresh-api'),

    # API Docs
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='api_docs'),
    # path('openapi', get_schema_view(title="Your Project", description="API for all things …"), name='openapi-schema'),
    # path('api/docs/', get_swagger_view(title='Your API Title')),
    # path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Edit Transaction Form
    # path('api/transactions/form/<int:transaction_id>/', TransactionFormAPIView.as_view(), name='transaction_form_api'),  # todo: create a separate, better suited form
]

# -------------------------
# Combine All URLs
# -------------------------
urlpatterns = frontend_urls + api_urls
