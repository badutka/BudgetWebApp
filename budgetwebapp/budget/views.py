import requests
import pandas as pd
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from rest_framework.exceptions import ValidationError

from api.views import BalanceHistoryAPIView
from .forms import BudgetExpenseEntryForm
from budget import models
from .models import (Transaction,
                     MoneyAccount,
                     Category, ParentCategory,
                     MonthlyCategorySummary,
                     MonthlyParentCategorySummary)

from .serializers import BalanceHistorySerializer, BalanceHistoryRefreshSerializer
from core.utils import (get_data_from_form,
                        get_response_by_status_code,
                        update_transactions_details,
                        flatten_querydict,
                        get_transactions_totals,
                        fetch_api_and_get_response)

from core.summaries import monthly_summary, monthly_summary_detailed


# ===============================================
#               BALANCE HISTORY
# ===============================================

def transactions_by_category_modal(request, category_id):
    # todo: check out if new serializer (api_transactions_by_category) could be better as ListCreateAPIView
    transactions_info = fetch_api_and_get_response(request, 'budget:api_transactions_by_category', 200, args=[category_id])
    transactions_stats = {k: v for k, v in transactions_info.items() if k != 'transactions'}

    categories = fetch_api_and_get_response(request, 'budget:categories', 200)
    category_map = {cat['id']: cat['name'] for cat in categories}
    category_name = category_map.get(category_id)

    chart_data = [
        {"x": transactions_stats['min'], "y": -0.5, "name": "Min"},
        {"x": transactions_stats['percentile_10'], "y": -0.5, "name": "10th %ile"},
        {"x": transactions_stats['average'], "y": -0.5, "name": "Mean"},
        {"x": transactions_stats['median'], "y": -0.5, "name": "Median"},
        {"x": transactions_stats['percentile_90'], "y": -0.5, "name": "90th %ile"},
        {"x": transactions_stats['max'], "y": -0.5, "name": "Max"},
    ]

    context = {
        'transactions': transactions_info['transactions'],
        'transactions_stats': transactions_stats,
        'category_name': category_name,
        "chart_data": chart_data
    }
    return render(request, 'budget/transactions_by_category_modal.html', context)


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

from django.db.models import Q
def balance_history_view_new(request, money_account_name):
    account = models.MoneyAccount.objects.get(name=money_account_name)
    transactions = models.Transaction.objects.filter(Q(origin__name=money_account_name) | Q(destination__name=money_account_name)).reverse()
    balance = account.starting_balance
    balance_history = []

    for transaction in transactions:
        old_balance = balance
        if transaction.origin and transaction.origin.name == money_account_name:
            amount = -transaction.amount
        elif transaction.destination and transaction.destination.name == money_account_name:
            amount = transaction.amount
        else:
            amount = 0

        balance += amount
        balance_history.append(
            {'date': transaction.date,
             'origin': transaction.origin,
             'destination': transaction.destination,
             'balance_before': old_balance,
             'balance_after': balance,
             'amount': amount,
             'transaction_type': transaction.transaction_type,
             }
        )

    context = {
        'balance_history': balance_history[::-1],
        'money_account_name': money_account_name
    }

    return render(request, 'budget/balance_history_new.html', context)


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
    monthly_summaries = fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, [('year', '2025')])
    print(monthly_summaries)
    context = {
        'monthly_data': monthly_summaries
    }
    return render(request, 'budget/chart_summary.html', context)


# ===============================================
#               TABLE SUMMARIES
# ===============================================


def monthly_summary_detailed_view(request):
    if request.method == 'GET':
        params = flatten_querydict(request.GET)

        all_summaries = fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, None)
        years = monthly_summary.get_available_years(all_summaries)
        year = request.GET.get('year', years)

        if 'year' not in request.GET and years:
            return redirect(f"{request.path}?year={years[-1]}")

        parent_categories = fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)
        monthly_parent_category_summaries = fetch_api_and_get_response(request,'budget:monthly_parent_category_summaries', 200, params)
        monthly_category_summaries = fetch_api_and_get_response(request, 'budget:monthly_category_summaries', 200, params)

        parent_categories_filtered = monthly_summary_detailed.get_filtered_parent_categories(request, parent_categories)

        summary = monthly_summary_detailed.get_summary_detailed(parent_categories_filtered, monthly_parent_category_summaries, monthly_category_summaries, 'expense')
        # todo: filter no-cat parent, filter 0-totals parent

        context = {
            'year': year,
            'years': years,
            'parent_categories': parent_categories,
            'summary': summary
        }

        if request.headers.get('HX-Request'):
            return render(request, 'budget/monthly_summary_detailed_table.html', context)

    return render(request, 'budget/monthly_summary_detailed.html', context)


def monthly_summary_view(request):
    if request.method == 'GET':
        params = flatten_querydict(request.GET)

        all_summaries = fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, None)
        years = monthly_summary.get_available_years(all_summaries)
        year = request.GET.get('year', years)

        if 'year' not in request.GET and years:
            return redirect(f"{request.path}?year={years[-1]}")

        # --- Fetch parent category summaries ---
        monthly_parent_category_summaries = fetch_api_and_get_response(request, 'budget:monthly_parent_category_summaries', 200, params)
        monthly_summaries = fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, params)

        # --- Pass API data to helpers ---
        incoming_rows, outgoing_rows = monthly_summary.get_parent_category_monthly_totals_rows(monthly_parent_category_summaries)

        if 'parent_category' in request.GET:
            starting_balance = monthly_summary.get_starting_balance(request, year)
            totals = monthly_summary.build_totals_rows(incoming_rows, outgoing_rows, starting_balance=starting_balance)
        else:
            totals = monthly_summary.get_totals_rows(monthly_summaries)

        parent_categories = fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)

        context = {
            'totals': totals,
            'incoming_rows': incoming_rows,
            'outgoing_rows': outgoing_rows,
            'year': year,
            'years': years,
            'parent_categories': parent_categories
        }

        if request.headers.get('HX-Request'):
            return render(request, 'budget/monthly_summary_table.html', context)

    return render(request, 'budget/monthly_summary.html', context)


# ===============================================
#                 CRUD + DUPLICATE
# ===============================================

def transactions_list_view(request):
    if request.method == 'GET':
        params = flatten_querydict(request.GET)

        transactions = fetch_api_and_get_response(request, 'budget:transactions_api', 200, params)
        money_accounts = fetch_api_and_get_response(request, 'budget:money_accounts', 200, params)
        categories = fetch_api_and_get_response(request, 'budget:categories', 200, params)
        parent_categories = fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)
        transactions = update_transactions_details(transactions, money_accounts, categories)

        paginator = Paginator(transactions, 30)  # 10 entries per page
        page_number = request.GET.get('page')
        transactions_page_obj = paginator.get_page(page_number)

        money_accounts_sum = sum(float(acc['balance']) for acc in money_accounts)
        totals, balance = get_transactions_totals(transactions)

        # Remove `page` from query params and encode the rest to preserve filters
        filter_params = request.GET.copy()
        if 'page' in filter_params:
            del filter_params['page']
        filter_query = filter_params.urlencode()

        context = {
            'sum_accs': money_accounts_sum,
            'totals': totals,
            'balance': balance,
            'transactions_page_obj': transactions_page_obj,
            'transaction_type_choices': Transaction.TRANSACTION_TYPE_CHOICES,
            'categories': categories,
            'parent_categories': parent_categories,
            'filter_query': filter_query,  # 🔥 needed for pagination links
        }

        if request.headers.get('HX-Request'):
            return render(request, 'budget/transactions_table.html', context)

        return render(request, 'budget/transactions.html', context)


def duplicate_transaction(request, transaction_id):
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST)
        if form.is_valid():
            api_url = request.build_absolute_uri(reverse('budget:transaction_duplicate_api', args=[transaction_id]))
            response = requests.post(api_url, data=get_data_from_form(form))
            return get_response_by_status_code(response, 204, HttpResponse(status=204), HttpResponseBadRequest())

    else:
        if not ('HX-Request' in request.headers):
            # Redirect users if accessing the URL directly
            return redirect(reverse_lazy('budget:transactions'))

        # Create a form instance with the existing entry data
        form = BudgetExpenseEntryForm(instance=Transaction.objects.get(id=transaction_id))

    return render(request, 'budget/transaction_add.html', {'form': form})


def transaction_add(request):
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST)

        if form.is_valid():
            api_url = request.build_absolute_uri(reverse('budget:transaction_add_api'))
            response = requests.post(api_url, data=get_data_from_form(form))
            return get_response_by_status_code(response, 201, HttpResponse(status=201), HttpResponseBadRequest())

    else:
        if not ('HX-Request' in request.headers):
            # Redirect users if accessing the URL directly
            return redirect(reverse_lazy('budget:transactions'))
        form = BudgetExpenseEntryForm()
    return render(request, 'budget/transaction_add.html', {'form': form})


def transaction(request, transaction_id):
    if request.method == 'GET':
        api_url = request.build_absolute_uri(
            reverse('budget:transaction_api', args=[transaction_id]))  # API endpoint URL
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
            # updated_transaction = form.save(commit=False)
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
