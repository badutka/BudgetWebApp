from collections import defaultdict

from django.db.models import Sum, Q
from decimal import Decimal
from calendar import month_name

from .models import (
    Transaction,
    Category,
    ParentCategory,
    MonthlySummary,
    MonthlyCategorySummary,
    MonthlyParentCategorySummary,
    MoneyAccount
)


def create_yearly_summary(year, skip_cat=None):
    # Get all months
    months = list(month_name)[1:]

    # Initialize the summary data
    summary = {
        'monthly_expenses': {k: v for k, v in zip(months, [0] * 12)},  # Total expenses for each month
        'monthly_income': {k: v for k, v in zip(months, [0] * 12)},  # Total income for each month
        'monthly_net_savings': {k: v for k, v in zip(months, [0] * 12)},  # Net savings for each month
        'monthly_ending_balance': {k: v for k, v in zip(months, [0] * 12)}  # Ending balance for each month
    }

    # Get starting balances from all MoneyAccounts
    starting_balance = MoneyAccount.objects.aggregate(total=Sum('starting_balance'))['total'] or 0

    # Calculate the summary for each month
    for month in range(1, 13):
        # get name for this month number
        this_month_name = months[month - 1]

        # Calculate the total expenses for the month
        expenses = Transaction.objects.filter(
            date__year=year,
            date__month=month,
            category__transaction_type='OUTGOING'
        ).aggregate(total=Sum('amount'))['total'] or 0
        summary['monthly_expenses'][this_month_name] = round(expenses, 2)

        # Calculate the total income for the month
        income = Transaction.objects.filter(
            date__year=year,
            date__month=month,
            category__transaction_type='INCOMING'
        ).aggregate(total=Sum('amount'))['total'] or 0
        summary['monthly_income'][this_month_name] = round(income, 2)

        # Calculate the net savings for the month
        net_savings = income - expenses
        summary['monthly_net_savings'][this_month_name] = round(net_savings, 2)

        # Calculate the ending balance for the month
        if month == 1:
            ending_balance = starting_balance + net_savings
            summary['monthly_ending_balance'][this_month_name] = round(ending_balance, 2)
        else:
            ending_balance = summary['monthly_ending_balance'][months[month - 2]] + net_savings
            summary['monthly_ending_balance'][this_month_name] = round(ending_balance, 2)

    total_expenses = sum(summary['monthly_expenses'].values())
    total_income = sum(summary['monthly_income'].values())
    total_net_savings = total_income - total_expenses
    total_ending_balance = starting_balance + total_net_savings

    return summary, {'total_expenses': total_expenses, 'total_income': total_income,
                     'total_net_savings': total_net_savings, 'total_ending_balance': total_ending_balance}


# longer updated version including non-transaction categories
def create_summary_table(year, option):
    summary_type = {"income": ['INNER', 'INCOMING'], "expense": ['INNER', 'OUTGOING']}
    months = list(month_name)[1:]

    # Fetch all parent categories that match the type
    parent_categories = ParentCategory.objects.filter(
        category__transaction_type__in=summary_type[option]
    ).distinct()
    # print(parent_categories)
    # Fetch all subcategories per parent category
    categories = Category.objects.filter(
        parent_category__in=parent_categories,
        transaction_type__in=summary_type[option]
    ).select_related('parent_category')

    # Fetch actual transaction summaries
    transactions = Transaction.objects.filter(
        year=year,
        transaction_type__in=summary_type[option]
    ).values(
        'category__parent_category__name',
        'category__name',
        'date__month'
    ).annotate(total_amount=Sum('amount'))

    # Build a transaction lookup dictionary
    tx_lookup = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for tx in transactions:
        parent = tx['category__parent_category__name']
        sub = tx['category__name']
        month = month_name[tx['date__month']]
        tx_lookup[parent][sub][month] = round(tx['total_amount'], 2)

    summary_table = {}
    category_totals = {}

    # Build the complete summary including categories without transactions
    for parent in parent_categories:
        parent_name = parent.name
        main_category_data = []
        category_monthly_totals = {month: 0 for month in months}
        category_total = 0

        subcategories = [cat for cat in categories if cat.parent_category_id == parent.id]
        # print(subcategories)
        for subcat in subcategories:
            subcat_name = subcat.name
            month_data = {month: tx_lookup[parent_name][subcat_name].get(month, 0) for month in months}
            total_for_sub = sum(month_data.values())

            for month in months:
                category_monthly_totals[month] += month_data[month]

            main_category_data.append({
                'subcategory': subcat_name,
                'summary': {**month_data, 'Total_for_sub': total_for_sub}
            })
            category_total += total_for_sub

        main_category_data.append({
            'total_per_month': category_monthly_totals
        })
        summary_table[parent_name] = main_category_data
        category_totals[parent_name] = category_total

    return summary_table, category_totals
