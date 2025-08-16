import requests

from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse

from budget.forms import BudgetExpenseEntryForm
from budget import models
from core import utils


def transactions_by_category_modal(request, category_id):
    # todo: check out if new serializer (api_transactions_by_category) could be better as ListCreateAPIView
    transactions_info = utils.fetch_api_and_get_response(request, 'budget:api_transactions_by_category', 200, args=[category_id])
    transactions_stats = {k: v for k, v in transactions_info.items() if k != 'transactions'}

    categories = utils.fetch_api_and_get_response(request, 'budget:categories', 200)
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
    return render(request, 'budget/transactions/transactions_by_category_modal.html', context)



def transactions_list_view(request):
    if request.method == 'GET':
        params = utils.flatten_querydict(request.GET)

        transactions = utils.fetch_api_and_get_response(request, 'budget:transactions_api', 200, params)
        money_accounts = utils.fetch_api_and_get_response(request, 'budget:money_accounts', 200, params)
        categories = utils.fetch_api_and_get_response(request, 'budget:categories', 200, params)
        parent_categories = utils.fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)
        transactions = utils.update_transactions_details(transactions, money_accounts, categories)

        paginator = Paginator(transactions, 30)  # 10 entries per page
        page_number = request.GET.get('page')
        transactions_page_obj = paginator.get_page(page_number)

        money_accounts_sum = sum(float(acc['balance']) for acc in money_accounts)
        totals, balance = utils.get_transactions_totals(transactions)

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
            'transaction_type_choices': models.Transaction.TRANSACTION_TYPE_CHOICES,
            'categories': categories,
            'parent_categories': parent_categories,
            'filter_query': filter_query,  # 🔥 needed for pagination links
        }

        if request.headers.get('HX-Request'):
            return render(request, 'budget/transactions/transactions_table.html', context)

        return render(request, 'budget/transactions/transactions.html', context)


def duplicate_transaction(request, transaction_id):
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST)
        if form.is_valid():
            api_url = request.build_absolute_uri(reverse('budget:transaction_duplicate_api', args=[transaction_id]))
            response = requests.post(api_url, data=utils.get_data_from_form(form))
            return utils.get_response_by_status_code(response, 204, HttpResponse(status=204), HttpResponseBadRequest())

    else:
        if not ('HX-Request' in request.headers):
            # Redirect users if accessing the URL directly
            return redirect(reverse_lazy('budget:transactions'))

        # Create a form instance with the existing entry data
        form = BudgetExpenseEntryForm(instance=models.Transaction.objects.get(id=transaction_id))

    return render(request, 'budget/transactions/transaction_add.html', {'form': form})


def transaction_add(request):
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST)

        if form.is_valid():
            api_url = request.build_absolute_uri(reverse('budget:transaction_add_api'))
            response = requests.post(api_url, data=utils.get_data_from_form(form))
            return utils.get_response_by_status_code(response, 201, HttpResponse(status=201), HttpResponseBadRequest())

    else:
        if not ('HX-Request' in request.headers):
            # Redirect users if accessing the URL directly
            return redirect(reverse_lazy('budget:transactions'))
        form = BudgetExpenseEntryForm()
    return render(request, 'budget/transactions/transaction_add.html', {'form': form})


def transaction(request, transaction_id):
    if request.method == 'GET':
        api_url = request.build_absolute_uri(
            reverse('budget:transaction_api', args=[transaction_id]))  # API endpoint URL
        response = requests.get(api_url)
        transactions = utils.get_response_by_status_code(response, 200, response.json(), [])

        transactions = [transactions]
        paginator = Paginator(transactions, 999)  # 10 entries per page
        page_number = request.GET.get('page')
        transactions_page_obj = paginator.get_page(page_number)

        context = {
            'transactions_page_obj': transactions_page_obj,
        }

        return render(request, 'budget/transactions/transactions.html', context)


def transaction_edit(request, transaction_id):
    transaction = get_object_or_404(models.Transaction, id=transaction_id)

    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST, instance=transaction)

        if form.is_valid():
            # updated_transaction = form.save(commit=False)
            api_url = request.build_absolute_uri(reverse('budget:transaction_update_api', args=[transaction_id]))
            response = requests.put(api_url, data=utils.get_data_from_form(form))
            return utils.get_response_by_status_code(response, 200, HttpResponse(status=200), HttpResponseBadRequest())

    else:
        if not ('HX-Request' in request.headers):
            return redirect(reverse_lazy('budget:transactions'))

        form = BudgetExpenseEntryForm(instance=transaction)

    return render(request, 'budget/transactions/transaction_form.html',
                  {'form': form, 'transaction_id': transaction_id})


def transaction_delete(request, transaction_id):
    api_url = request.build_absolute_uri(reverse('budget:transaction_delete_api', args=[transaction_id]))

    if request.method == 'GET':
        response = requests.delete(api_url)
        return utils.get_response_by_status_code(response, 200, redirect('budget:transactions'))

    return redirect('budget:transactions')

# return render(request, 'confirmation_template.html', {'entry': entry})
