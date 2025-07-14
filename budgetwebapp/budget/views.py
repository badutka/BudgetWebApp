import requests, json
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpResponse, HttpRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from rest_framework.exceptions import ValidationError
from django.http import JsonResponse

from api.views import BalanceHistoryAPIView
from .forms import BudgetExpenseEntryForm
from .models import (Transaction,
                     MoneyAccount,
                     Category, ParentCategory,
                     MonthlyCategorySummary,
                     MonthlyParentCategorySummary,
                     MonthlySummary)
from .serializers import BalanceHistorySerializer, BalanceHistoryRefreshSerializer
from .summary import create_summary_table, create_yearly_summary
from .utils import (get_data_from_form,
                    get_response_by_status_code,
                    update_transactions_details,
                    flatten_querydict,
                    get_transactions_totals,
                    fetch_api_and_get_response,
                    SummaryViewUtils)
from .filters import TransactionFilter


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
    summary, totals = create_yearly_summary(2025)
    expense_summary_detailed, total_expense_summary_detailed = create_summary_table(2025, "expense")
    income_summary_detailed, total_income_summary_detailed = create_summary_table(2025, "income")

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
    summary_table, summary_table_total = create_summary_table(2025, "expense")

    context = {
        'summary_table': summary_table,
        'summary_table_total': summary_table_total
    }

    return render(request, 'budget/monthly_expense_summary.html', context)


def chunked(iterable, size):
    """Yield successive chunks of given size from iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def product_list(summaries):
    rows = list(chunked(summaries, 12))
    return rows


from collections import defaultdict
from django.db.models import Q


def get_parent_category_summary_rows(year, transaction_type=None):
    """
    Returns a list of dicts representing rows:
    Each dict has keys: is_parent_category (bool), name (str), amounts (list of 13 decimals)
    The last element (index 12) is the sum of the first 12 monthly amounts.

    Optionally filters by transaction_type.
    """

    # Base queryset filters
    category_filter = Q(year=year)
    parent_filter = Q(year=year)

    if transaction_type:
        category_filter &= Q(transaction_type=transaction_type)
        parent_filter &= Q(transaction_type=transaction_type)

    # Fetch summaries with filters
    category_summaries = MonthlyCategorySummary.objects.filter(category_filter)
    parent_summaries = MonthlyParentCategorySummary.objects.filter(parent_filter)

    # Prepare defaultdicts for amounts (12 months indexed 0-11)
    category_amounts = defaultdict(lambda: [0] * 12)
    for s in category_summaries:
        category_amounts[(s.parent_category_name, s.category_name)][s.month - 1] = s.amount

    parent_amounts = defaultdict(lambda: [0] * 12)
    for s in parent_summaries:
        parent_amounts[s.parent_category_name][s.month - 1] = s.amount

    # Query parent categories with prefetched categories
    parents = ParentCategory.objects.all().order_by('name').prefetch_related('category_set')

    result_rows = []

    for parent in parents:
        # Prepare amounts list with total sum as 13th value
        parent_values = parent_amounts.get(parent.name, [0] * 12)
        parent_sum = sum(parent_values)
        result_rows.append({
            'is_parent_category': True,
            'name': parent.name,
            'amounts': parent_values + [parent_sum],
        })

        # Add child categories rows with sums
        categories = parent.category_set.all().order_by('name')
        for cat in categories:
            cat_values = category_amounts.get((parent.name, cat.name), [0] * 12)
            cat_sum = sum(cat_values)
            result_rows.append({
                'is_parent_category': False,
                'name': cat.name,
                'amounts': cat_values + [cat_sum],
            })

    return result_rows


def monthly_summary_detailed_view(request):
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']

    rows = get_parent_category_summary_rows(2025)

    context = {
        "months": months,
        'rows': rows
    }

    return render(request, 'budget/monthly_summary_detailed.html', context)


def monthly_summary_view(request):
    if request.method == 'GET':

        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        params = flatten_querydict(request.GET)
        # --- Fetch parent category summaries ---
        monthly_parent_category_summaries = fetch_api_and_get_response(request, 'budget:monthly_parent_category_summaries', 200, params)
        monthly_summaries = fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, params)

        # --- Pass API data to helpers ---
        incoming_rows, outgoing_rows = SummaryViewUtils.get_parent_type_rows_separated(monthly_parent_category_summaries)
        if 'parent_category' in request.GET:
            totals = SummaryViewUtils.build_summary_totals(incoming_rows, outgoing_rows, starting_balance=float(monthly_summaries[0]['ending_balance']))
        else:
            totals = SummaryViewUtils.get_summary_rows(monthly_summaries)

        all_summaries = fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, None)  # No filters
        years = SummaryViewUtils.get_available_years(all_summaries)
        year = request.GET.get('year', years)

        parent_categories = fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)

        if 'year' not in request.GET and years:
            return redirect(f"{request.path}?year={years[-1]}")

        context = {
            "months": months,
            'totals': totals,
            'incoming_rows': incoming_rows,
            'outgoing_rows': outgoing_rows,
            'year': year,
            'years': years,
            'parent_categories': parent_categories
        }

        if request.headers.get('HX-Request'):
            return render(request, 'budget/monthly_summary_tbl.html', context)

    return render(request, 'budget/monthly_summary.html', context)


def monthly_income_summary_view(request):
    summary_table, summary_table_total = create_summary_table(2025, "income")

    context = {
        'summary_table': summary_table,
        'summary_table_total': summary_table_total
    }

    return render(request, 'budget/monthly_income_summary.html', context)


# ===============================================
#                 CRUD + DUPLICATE
# ===============================================

def transactions_list_view(request):
    if request.method == 'GET':
        api_url = request.build_absolute_uri(reverse('budget:transactions_api'))  # API endpoint URL
        # response = requests.get(api_url)
        params = flatten_querydict(request.GET)
        response = requests.get(api_url, params=params)

        transactions = get_response_by_status_code(response, 200, response.json(), [])
        money_accounts = MoneyAccount.objects.all()
        categories = Category.objects.all()
        parent_categories = ParentCategory.objects.all()
        transactions = update_transactions_details(transactions, money_accounts, categories)

        paginator = Paginator(transactions, 30)  # 10 entries per page
        page_number = request.GET.get('page')
        transactions_page_obj = paginator.get_page(page_number)

        money_accounts_sum = money_accounts.aggregate(total=Sum('balance'))['total']
        totals, balance = get_transactions_totals(transactions)

        # Remove `page` from query params and encode the rest to preserve filters
        filter_params = request.GET.copy()
        if 'page' in filter_params:
            del filter_params['page']
        filter_query = filter_params.urlencode()

        context = {
            'transactions_page_obj': transactions_page_obj,
            'sum_accs': round(money_accounts_sum, 2),
            'transaction_type_choices': Transaction.TRANSACTION_TYPE_CHOICES,
            'categories': categories,
            'parent_categories': parent_categories,
            'totals': totals,
            'balance': balance,
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
