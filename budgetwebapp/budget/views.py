import requests
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView
from django.db.models import Sum

from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import BudgetExpenseEntryForm
from .models import Transaction, MoneyAccount, BalanceHistory
from .summary import create_summary_table, create_yearly_summary
from .serializers import ChartDataSerializer


class BalanceHistoryView(ListView):
    model = BalanceHistory
    template_name = 'budget/balance_history.html'
    context_object_name = 'balance_entries'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        money_account_name = self.kwargs['money_account_name']
        money_account = MoneyAccount.objects.get(name=money_account_name)
        balance_history = BalanceHistory.objects.filter(money_account=money_account)
        # balance_history = BalanceHistory.objects.filter(money_account=money_account).order_by('-created_at')
        context['money_account_name'] = money_account_name
        context['balance_history'] = balance_history
        return context


class ChartDataAPIView(APIView):
    def get(self, request, format=None):
        summary, totals = create_yearly_summary(2023)

        serializer = ChartDataSerializer(summary)

        return Response(serializer.data)


def chart_summary(request):
    context = {

    }

    return render(request, 'budget/chart_summary.html', context)


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


def transactions_list_view(request):
    entries = Transaction.objects.all()
    # entries = BudgetExpenseEntry.objects.all().order_by('-created_at')
    accs = MoneyAccount.objects.all().aggregate(total=Sum('balance'))['total']

    paginator = Paginator(entries, 999)  # 10 entries per page
    page_number = request.GET.get('page')
    transactions_page_obj = paginator.get_page(page_number)

    context = {
        'transactions_page_obj': transactions_page_obj,
        'sum_accs': round(accs, 2)
    }

    return render(request, 'budget/transactions.html', context)


def transaction_add(request):
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('budget:transactions')
    else:
        form = BudgetExpenseEntryForm()
    return render(request, 'budget/transaction_add.html', {'form': form})


def transaction_edit(request, transaction_id):
    entry = Transaction.objects.get(id=transaction_id)
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('budget:transactions')
    else:
        form = BudgetExpenseEntryForm(instance=entry)
    return render(request, 'budget/transaction_edit.html', {'form': form, 'transaction_id': transaction_id})


def transaction_remove(request, transaction_id):
    entry = Transaction.objects.get(id=transaction_id)
    entry.delete()
    return redirect('budget:transactions')
