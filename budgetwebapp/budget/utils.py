from datetime import datetime


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


def ts_to_readable(timestamp_str):
    timestamp = datetime.fromisoformat(timestamp_str[:-1])  # Remove trailing 'Z'
    return timestamp.strftime('%Y-%m-%d %I:%M %p')
    # return timestamp.strftime('%b %d, %Y %I:%M %p')
