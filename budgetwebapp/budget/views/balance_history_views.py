from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from rest_framework.exceptions import ValidationError

from api.views import BalanceHistoryAPIView
from budgetwebapp.budget import models
from budgetwebapp.budget import serializers


def refresh_balance_history(request, money_account_name):
    serializer = serializers.BalanceHistoryRefreshSerializer(data={'money_account_name': money_account_name})

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
    # print(balance_history[::-1])
    return render(request, 'budget/balance_history/balance_history_new.html', context)


def balance_history_view(request, money_account_name):
    balance_history_api_view = BalanceHistoryAPIView.as_view()
    response = balance_history_api_view(request, money_account_name=money_account_name)
    serializer = serializers.BalanceHistorySerializer(data=response.data, many=True)
    serializer.is_valid()
    balance_history = serializer.validated_data

    context = {
        'balance_history': balance_history,
        'money_account_name': money_account_name
    }

    return render(request, 'budget/balance_history/balance_history.html', context)
