import requests
from datetime import datetime
from collections import defaultdict

from django.http import HttpResponseBadRequest, HttpResponse, HttpRequest
from django.urls import reverse
from django.db.models import Q


def get_data_from_form(form):
    """
    # Prepare data for API request
    :param form:
    :return:
    """
    data = {
        'date': form.cleaned_data['date'],
        'category': form.cleaned_data['category'].pk,
        'amount': form.cleaned_data['amount'],
        # 'origin': form.cleaned_data['origin'],
        # 'destination': form.cleaned_data['destination'],
        'origin': form.cleaned_data['origin'].pk if form.cleaned_data['origin'] else None,
        'destination': form.cleaned_data['destination'].pk if form.cleaned_data['destination'] else None,
        'description': form.cleaned_data['description'],
    }
    return data


def get_response_by_status_code(response, status_code, responseA, responseB=None):
    """

    :param response:
    :param status_code:
    :param responseA:
    :param responseB:
    :return:
    """
    if response.status_code == status_code:
        return responseA
    elif responseB is not None:
        # Handle error case
        return responseB


def fetch_api_and_get_response(
        request: HttpRequest,
        api_url: str,
        status_code_expected: int,
        params: list[tuple[str, str]] | None = None,
        response_failure: HttpResponse | None = None
) -> HttpResponse:
    """
    Fetches a response from an internal API endpoint and returns a processed HttpResponse.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        api_url (str): The name of the URL pattern to reverse for the API endpoint.
        status_code_expected (int): The expected HTTP status code from the API response.
        params (list[tuple[str, str]] | None): Optional list of query parameter key-value pairs.
        response_failure (HttpResponse | None): Response to return if API status code is unexpected.

    Returns:
        HttpResponse: A response based on the API call result and status code check.
    """
    absolute_api_uri = request.build_absolute_uri(reverse(api_url))
    parent_response = requests.get(absolute_api_uri, params=params)
    response_failure = response_failure if response_failure else HttpResponseBadRequest()
    response = get_response_by_status_code(
        parent_response,
        status_code_expected,
        parent_response.json(),
        response_failure
    )
    return response


def update_request_data_for_transaction(request):
    data = request.data.copy()

    # Pre-fill missing fields from the model instance
    if 'origin' not in data:
        data['origin'] = ''  # now 'origin' will be included

    if 'destination' not in data:
        data['destination'] = ''  # example for destination to

    return data


def flatten_querydict(querydict):
    """
    Convert a Django QueryDict into a list of tuples suitable for requests.get(params=...)
    Preserves multiple values for the same key.
    This ensures that django filter works properly with ApiView (otherwise only 1 category is passed).
    That's because of interface mismatch between Django’s multi-value QueryDict and requests params.
    """
    return list(querydict.lists())


def ts_to_readable(timestamp_str):
    timestamp = datetime.fromisoformat(timestamp_str[:-1])  # Remove trailing 'Z'
    return timestamp.strftime('%Y-%m-%d %I:%M %p')
    # return timestamp.strftime('%b %d, %Y %I:%M %p')


def update_transactions_details(transactions, money_accounts, categories):
    account_map = {acc.id: acc.name for acc in money_accounts}
    category_map = {cat.id: str(cat) for cat in categories}

    for t9n in transactions:
        origin_id = t9n.get('origin')
        destination_id = t9n.get('destination')
        category_id = t9n.get('category')
        created_at = t9n.get('created_at')
        updated_at = t9n.get('updated_at')

        t9n['origin'] = account_map.get(origin_id) if origin_id is not None else "Out"
        t9n['destination'] = account_map.get(destination_id) if destination_id is not None else "Out"
        t9n['category'] = category_map.get(category_id) if category_id is not None else None
        t9n['created_at'] = ts_to_readable(created_at)
        t9n['updated_at'] = ts_to_readable(updated_at)

    return transactions


def get_transactions_totals(transactions):
    totals = {
        'INNER': 0,
        'INCOMING': 0,
        'OUTGOING': 0
    }

    for t9n in transactions:
        t9n_type = t9n.get('transaction_type')
        amount = float(t9n.get('amount', 0))

        if t9n_type in totals:
            totals[t9n_type] += amount

    balance = round(totals['INCOMING'] - totals['OUTGOING'], 2)
    totals = {k: round(v, 2) for k, v in totals.items()}

    return totals, balance


class SummaryViewUtils:
    @staticmethod
    def get_summary_rows(data):
        income = [0] * 12
        expenses = [0] * 12
        net_savings = [0] * 12
        ending_balance = [0] * 12

        for s in data:
            idx = s['month'] - 1
            income[idx] = float(s['income'])
            expenses[idx] = float(s['expenses'])
            net_savings[idx] = float(s['net_savings'])
            ending_balance[idx] = float(s['ending_balance'])

        return [
            {
                'name': 'Income',
                'amounts': income + [sum(income)],
            },
            {
                'name': 'Expenses',
                'amounts': expenses + [sum(expenses)],
            },
            {
                'name': 'Net Savings',
                'amounts': net_savings + [sum(net_savings)],
            },
            {
                'name': 'Ending Balance',
                'amounts': ending_balance + [ending_balance[-1] if any(ending_balance) else 0],
            }
        ]

    @staticmethod
    def get_parent_type_rows_separated(data):
        income_totals = defaultdict(lambda: [0] * 12)
        expense_totals = defaultdict(lambda: [0] * 12)

        for s in data:
            idx = s['month'] - 1
            if s['transaction_type'] == 'INCOMING':
                income_totals[s['parent_category_name']][idx] += float(s['amount'])
            elif s['transaction_type'] == 'OUTGOING':
                expense_totals[s['parent_category_name']][idx] += float(s['amount'])

        def build_rows(source_dict):
            rows = []
            for parent_name in sorted(source_dict.keys()):
                vals = source_dict[parent_name]
                rows.append({
                    'name': parent_name,
                    'amounts': vals + [sum(vals)],
                })
            return rows

        return build_rows(income_totals), build_rows(expense_totals)

    @staticmethod
    def build_summary_totals(income_rows, expense_rows, starting_balance=0.0):
        def sum_vertically(rows):
            totals = [0.0] * 13
            for row in rows:
                for i in range(13):
                    totals[i] += row['amounts'][i]
            return totals

        income_total = sum_vertically(income_rows)
        expense_total = sum_vertically(expense_rows)

        # Net savings: monthly income - expense
        net_savings = [income_total[i] - expense_total[i] for i in range(12)]
        net_savings.append(sum(net_savings))  # 13th value is total

        # Ending balance: cumulative net savings starting from a given balance
        ending_balance = []
        running_balance = starting_balance
        for ns in net_savings[:12]:
            running_balance += ns
            ending_balance.append(running_balance)
        ending_balance.append(running_balance)  # 13th value same as last month

        return [
            {'name': 'Income', 'amounts': income_total},
            {'name': 'Expenses', 'amounts': expense_total},
            {'name': 'Net Savings', 'amounts': net_savings},
            {'name': 'Ending Balance', 'amounts': ending_balance},
        ]

    @staticmethod
    def get_available_years(monthly_summaries):
        return sorted({s['year'] for s in monthly_summaries}, reverse=True)
