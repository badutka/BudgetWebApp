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
        'origin': form.cleaned_data['origin'],
        'destination': form.cleaned_data['destination'],
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
