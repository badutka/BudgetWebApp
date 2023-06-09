from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic.edit import CreateView
from django.shortcuts import render, redirect
from django.core.paginator import Paginator

from .models import BudgetExpenseEntry
from .forms import BudgetExpenseEntryForm

from django.views.generic import ListView
from .models import BudgetExpenseEntry, create_summary_table

def yearly_summary_view(request):

    summary_table, summary_table_total = create_summary_table(2023)

    context = {
        'summary_table': summary_table,
        'summary_table_total': summary_table_total
    }

    return render(request, 'budget/yearly_summary.html', context)

def outgoing_transaction_list_view(request):
    entries = BudgetExpenseEntry.objects.filter(transaction_type__in=['OUTGOING', 'INNER']).order_by('date')

    paginator = Paginator(entries, 5)  # 10 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }

    return render(request, 'budget/outgoing_transactions.html', context)


def incoming_transaction_list_view(request):
    entries = BudgetExpenseEntry.objects.filter(transaction_type__in=['INCOMING', 'INNER']).order_by('date')

    paginator = Paginator(entries, 5)  # 10 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }

    return render(request, 'budget/incoming_transactions.html', context)


def budget_expense_entry_list(request):
    entries = BudgetExpenseEntry.objects.all().order_by('date')

    paginator = Paginator(entries, 5)  # 10 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }

    return render(request, 'budget/entry_list.html', context)


def budget_entry_add(request):
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('budget:budget_expense_entry_list')
    else:
        form = BudgetExpenseEntryForm()
    return render(request, 'budget/entry_add.html', {'form': form})


def budget_entry_edit(request, entry_id):
    entry = BudgetExpenseEntry.objects.get(id=entry_id)
    if request.method == 'POST':
        form = BudgetExpenseEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('budget:budget_expense_entry_list')
    else:
        form = BudgetExpenseEntryForm(instance=entry)
    return render(request, 'budget/entry_edit.html', {'form': form, 'entry_id': entry_id})


def budget_entry_remove(request, entry_id):
    entry = BudgetExpenseEntry.objects.get(id=entry_id)
    entry.delete()
    return redirect('budget:budget_expense_entry_list')
