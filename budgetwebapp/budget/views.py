import requests
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from rest_framework.exceptions import ValidationError

from api.views import BalanceHistoryAPIView
from .forms import BudgetExpenseEntryForm
from .models import Transaction, MoneyAccount
from .serializers import BalanceHistorySerializer, BalanceHistoryRefreshSerializer
from .summary import create_summary_table, create_yearly_summary
from .utils import get_data_from_form, get_response_by_status_code


# ===============================================
#               BALANCE HISTORY
# ===============================================

def refresh_balance_history(request, money_account_name):
    serializer = BalanceHistoryRefreshSerializer(data={'money_account_name': money_account_name})

    try:  # or just do serializer.is_valid(raise_exception=True) instead of try/except for default handling
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        error_message = str(e.detail)
        # Handle the validation error as needed
        # For example, you can return a custom error response
        return HttpResponseBadRequest(error_message)

    message = serializer.create(serializer.validated_data)['message']
    return redirect('budget:balance_history', money_account_name=money_account_name)

    # response = balance_history_view(request, money_account_name=money_account_name)
    # return response


def balance_history_view(request, money_account_name):
    balance_history_api_view = BalanceHistoryAPIView.as_view()
    response = balance_history_api_view(request, money_account_name=money_account_name)
    serializer = BalanceHistorySerializer(data=response.data, many=True)
    serializer.is_valid()
    balance_history = serializer.validated_data

    context = {
        'balance_history': balance_history,
        'money_account_name': money_account_name
    }

    return render(request, 'budget/balance_history.html', context)


# ===============================================
#                    CHARTS
# ===============================================

def chart_summary(request):
    context = {}
    return render(request, 'budget/chart_summary.html', context)


# ===============================================
#               TABLE SUMMARIES
# ===============================================

def yearly_expense_summary_view(request):
    summary, totals = create_yearly_summary(2023)
    expense_summary_detailed, total_expense_summary_detailed = create_summary_table(2023, "expense")
    income_summary_detailed, total_income_summary_detailed = create_summary_table(2023, "income")

    context = {
        'summary': summary,
        'totals': totals,
        'expense_summary_detailed': expense_summary_detailed,
        'total_expense_summary_detailed': total_expense_summary_detailed,
        'income_summary_detailed': income_summary_detailed,
        'total_income_summary_detailed': total_income_summary_detailed
    }

    return render(request, 'budget/yearly_expense_summary.html', context)


def monthly_expense_summary_view(request):
    summary_table, summary_table_total = create_summary_table(2023, "expense")

    context = {
        'summary_table': summary_table,
        'summary_table_total': summary_table_total
    }

    return render(request, 'budget/monthly_expense_summary.html', context)


def monthly_income_summary_view(request):
    summary_table, summary_table_total = create_summary_table(2023, "income")

    context = {
        'summary_table': summary_table,
        'summary_table_total': summary_table_total
    }

    return render(request, 'budget/monthly_income_summary.html', context)


# ===============================================
#        INCOMING / OUTGOING TRANSACTIONS
# ===============================================

def outgoing_transactions_list_view(request):
    entries = Transaction.objects.filter(transaction_type__in=['OUTGOING', 'INNER']).order_by('date')

    paginator = Paginator(entries, 999)  # 10 entries per page
    page_number = request.GET.get('page')
    transactions_page_obj = paginator.get_page(page_number)

    context = {
        'transactions_page_obj': transactions_page_obj
    }

    return render(request, 'budget/transactions_outgoing.html', context)


def incoming_transactions_list_view(request):
    entries = Transaction.objects.filter(transaction_type__in=['INCOMING', 'INNER']).order_by('date')

    paginator = Paginator(entries, 999)  # 10 entries per page
    page_number = request.GET.get('page')
    transactions_page_obj = paginator.get_page(page_number)

    context = {
        'transactions_page_obj': transactions_page_obj
    }

    return render(request, 'budget/transactions_incoming.html', context)


# ===============================================
#                 CRUD + DUPLICATE
# ===============================================


def transactions_list_view(request):
    if request.method == 'GET':
        api_url = request.build_absolute_uri(reverse('budget:transactions_api'))  # API endpoint URL
        response = requests.get(api_url)
        transactions = get_response_by_status_code(response, 200, response.json(), [])

        mountAccounts = MoneyAccount.objects.all().aggregate(total=Sum('balance'))['total']
        paginator = Paginator(transactions, 999)  # 10 entries per page
        page_number = request.GET.get('page')
        transactions_page_obj = paginator.get_page(page_number)

        context = {
            'transactions_page_obj': transactions_page_obj,
            'sum_accs': round(mountAccounts, 2)
        }

        return render(request, 'budget/transactions.html', context)


def duplicate_transaction(request, transaction_id):
    # Get the existing transaction entry
    existing_transaction = Transaction.objects.get(id=transaction_id)

    if request.method == 'POST':
        # Create a form instance with the POST data
        form = BudgetExpenseEntryForm(request.POST)
        if form.is_valid():
            # Save the duplicated entry
            new_transaction = form.save(commit=False)
            new_transaction.pk = None  # Clear the primary key to create a new entry
            new_transaction.save()

            return HttpResponse(status=204)
    else:
        if not ('HX-Request' in request.headers):
            # Redirect users if accessing the URL directly
            return redirect(reverse_lazy('budget:transactions'))

        # Create a form instance with the existing entry data
        form = BudgetExpenseEntryForm(instance=existing_transaction)

    return render(request, 'budget/transaction_add.html', {'form': form})


def transaction_add(request):
    if request.method == 'POST':

        form = BudgetExpenseEntryForm(request.POST)

        if form.is_valid():
            api_url = request.build_absolute_uri(reverse('budget:transaction_add_api'))
            response = requests.post(api_url, data=get_data_from_form(form))
            return get_response_by_status_code(response, 204, HttpResponse(status=204), HttpResponseBadRequest())

    else:
        if not ('HX-Request' in request.headers):
            # Redirect users if accessing the URL directly
            return redirect(reverse_lazy('budget:transactions'))

        form = BudgetExpenseEntryForm()
    return render(request, 'budget/transaction_add.html', {'form': form})


def transaction(request, transaction_id):
    if request.method == 'GET':
        api_url = request.build_absolute_uri(reverse('budget:transaction_api', args=[transaction_id]))  # API endpoint URL
        response = requests.get(api_url)
        transactions = get_response_by_status_code(response, 200, response.json(), [])

        transactions = [transactions]
        paginator = Paginator(transactions, 999)  # 10 entries per page
        page_number = request.GET.get('page')
        transactions_page_obj = paginator.get_page(page_number)

        context = {
            'transactions_page_obj': transactions_page_obj,
        }

        return render(request, 'budget/transactions.html', context)


def transaction_edit(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)

    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST, instance=transaction)

        if form.is_valid():
            api_url = request.build_absolute_uri(reverse('budget:transaction_update_api', args=[transaction_id]))
            response = requests.put(api_url, data=get_data_from_form(form))
            return get_response_by_status_code(response, 200, HttpResponse(status=200), HttpResponseBadRequest())

    else:
        if not ('HX-Request' in request.headers):
            return redirect(reverse_lazy('budget:transactions'))

        form = BudgetExpenseEntryForm(instance=transaction)

    return render(request, 'budget/transaction_form.html', {'form': form, 'transaction_id': transaction_id})


def transaction_delete(request, transaction_id):
    api_url = request.build_absolute_uri(reverse('budget:transaction_delete_api', args=[transaction_id]))

    if request.method == 'GET':
        response = requests.delete(api_url)
        return get_response_by_status_code(response, 200, redirect('budget:transactions'))

    return redirect('budget:transactions')

# return render(request, 'confirmation_template.html', {'entry': entry})
