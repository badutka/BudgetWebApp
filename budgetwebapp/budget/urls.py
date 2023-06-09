from django.urls import path
from .views import (
    budget_expense_entry_list,
    budget_entry_add,
    budget_entry_edit,
    budget_entry_remove,
    incoming_transaction_list_view,
    outgoing_transaction_list_view,
    yearly_summary_view,
)

urlpatterns = [
    path('', budget_expense_entry_list, name='budget_expense_entry_list'),
    path('add/', budget_entry_add, name='budget_entry_add'),
    path('edit/<int:entry_id>/', budget_entry_edit, name='budget_entry_edit'),
    path('remove/<int:entry_id>/', budget_entry_remove, name='budget_entry_remove'),
    path('transactions/incoming/', incoming_transaction_list_view, name='incoming_transactions'),
    path('transactions/outgoing/', outgoing_transaction_list_view, name='outgoing_transactions'),
    path('transactions/summary/', yearly_summary_view, name='yearly_summary'),
    # path('transactions/outgoing/', OutgoingTransactionListView.as_view(), name='outgoing_transactions'),
]