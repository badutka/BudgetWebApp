from django.db.models import Sum
from calendar import month_name

from .models import MainCategory, SubCategory, BudgetExpenseEntry, MoneyAccount


def create_yearly_summary(year):
    # Get all months
    months = list(month_name)[1:]

    # Initialize the summary data
    summary = {
        'monthly_expenses': {k: v for k, v in zip(months, [0] * 12)},  # Total expenses for each month
        'monthly_income': {k: v for k, v in zip(months, [0] * 12)},  # Total income for each month
        'monthly_net_savings': {k: v for k, v in zip(months, [0] * 12)},  # Net savings for each month
        'monthly_ending_balance': {k: v for k, v in zip(months, [0] * 12)}  # Ending balance for each month
    }

    # Get the starting balances for each money account
    pko_account = MoneyAccount.objects.get(name='PKO')
    ing_account = MoneyAccount.objects.get(name='ING')
    cash_account = MoneyAccount.objects.get(name='CASH')

    # Calculate the starting balance for the month
    starting_balance = pko_account.starting_balance + ing_account.starting_balance + cash_account.starting_balance

    # Calculate the summary for each month
    for month in range(1, 13):
        # get name for this month number
        this_month_name = months[month - 1]

        # Calculate the total expenses for the month
        expenses = BudgetExpenseEntry.objects.filter(
            date__year=year,
            date__month=month,
            transaction_type='OUTGOING'
        ).aggregate(total=Sum('amount'))['total'] or 0
        summary['monthly_expenses'][this_month_name] = round(expenses, 2)

        # Calculate the total income for the month
        income = BudgetExpenseEntry.objects.filter(
            date__year=year,
            date__month=month,
            transaction_type='INCOMING'
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

    return summary, {'total_expenses': total_expenses, 'total_income': total_income, 'total_net_savings': total_net_savings, 'total_ending_balance': total_ending_balance}


# def create_yearly_summary(year):
#     # Prepare types of transactions to summarize
#     summary_type = {
#         "income": ['INNER', 'INCOMING'],
#         "expense": ['INNER', 'OUTGOING']
#     }
#
#     # Get all main categories
#     main_categories = MainCategory.objects.all()
#
#     # Get all months
#     months = list(month_name)[1:]
#
#     # Initialize dictionaries to store totals
#     monthly_expenses = {month: 0 for month in months}
#     monthly_income = {month: 0 for month in months}
#     monthly_net_savings = {month: 0 for month in months}
#
#     # Loop through each main category
#     for main_category in main_categories:
#         # Get all subcategories for the current main category
#         subcategories = SubCategory.objects.filter(category__main_category=main_category)
#
#         # Loop through each subcategory
#         for subcategory in subcategories:
#             # Query the BudgetExpenseEntry model to get the monthly summary for the given year and category
#             monthly_summary = BudgetExpenseEntry.objects.filter(
#                 category__main_category=main_category,
#                 category__subcategory=subcategory,
#                 year=year,
#                 transaction_type__in=summary_type["expense"] + summary_type["income"]
#             ).values('date__month', 'transaction_type').annotate(total_amount=Sum('amount'))
#
#             # Loop through the monthly summary data
#             for entry in monthly_summary:
#                 month = month_name[entry['date__month']]
#                 total_amount = round(entry['total_amount'], 2)
#                 transaction_type = entry['transaction_type']
#
#                 # Update monthly totals
#                 if transaction_type in summary_type["expense"]:
#                     monthly_expenses[month] += total_amount
#                 elif transaction_type in summary_type["income"]:
#                     monthly_income[month] += total_amount
#
#     # Calculate monthly net savings
#     for month in months:
#         monthly_net_savings[month] = monthly_income[month] - monthly_expenses[month]
#
#     # Calculate total expenses, total income, and total net savings
#     total_expenses = sum(monthly_expenses.values())
#     total_income = sum(monthly_income.values())
#     total_net_savings = total_income - total_expenses
#
#     return ({"monthly_expenses": monthly_expenses, "monthly_income": monthly_income, "monthly_net_savings": monthly_net_savings},
#             {"total_expenses": total_expenses, "total_income": total_income, "total_net_savings": total_net_savings})


def create_summary_table(year, option):
    # Prepare types of transactions to summarize
    summary_type = {"income": ['INNER', 'INCOMING'], "expense": ['INNER', 'OUTGOING']}

    # # Get all main categories
    # main_categories = MainCategory.objects.all()

    # Get all main categories based on the transaction type
    main_categories = MainCategory.objects.filter(category__transaction_type__in=summary_type[option]).distinct()

    # Create a dictionary to store the summary data
    summary_table = {}

    # Get all months
    months = list(month_name)[1:]

    # Initialize a dictionary to store the category totals across all subcategories and months
    category_totals = {}

    # Loop through each main category
    for main_category in main_categories:
        # Get all subcategories for the current main category
        subcategories = SubCategory.objects.filter(category__main_category=main_category)
        # Create a list to store the row data for the current main category
        main_category_data = []

        # Initialize variables for total amounts
        category_total = 0
        subcategory_totals = {}

        # Initialize a dictionary to store the monthly totals per category across all subcategories
        category_monthly_totals = {month: 0 for month in months}

        # Loop through each subcategory
        for subcategory in subcategories:
            # Query the BudgetExpenseEntry model to get the monthly summary for the given year
            monthly_summary = BudgetExpenseEntry.objects.filter(
                category__main_category=main_category,
                category__subcategory=subcategory,
                year=year,
                transaction_type__in=summary_type[option]  # Filter for income or expense transactions
            ).values('date__month').annotate(total_amount=Sum('amount'))

            total_for_sub = 0

            # Create a dictionary to store the monthly summary for the subcategory
            subcategory_summary = {month: 0 for month in months}
            # Loop through the monthly summary data
            for entry in monthly_summary:
                month = month_name[entry['date__month']]
                total_amount = round(entry['total_amount'], 2)
                subcategory_summary[month] = total_amount

                # Update subcategory total
                if subcategory in subcategory_totals:
                    subcategory_totals[subcategory] += total_amount
                else:
                    subcategory_totals[subcategory] = total_amount

                # Update category total
                category_total += total_amount
                total_for_sub += total_amount

                # Update monthly totals per category across all subcategories
                if month in category_monthly_totals:
                    category_monthly_totals[month] += total_amount
                else:
                    category_monthly_totals[month] = total_amount

            subcategory_summary["Total_for_sub"] = total_for_sub

            # Append the subcategory summary to the main category data list
            main_category_data.append({
                'subcategory': subcategory.name,
                'summary': subcategory_summary
            })

        main_category_data.append({
            'total_per_month': category_monthly_totals
        })

        # Add the main category data to the summary table dictionary
        summary_table[main_category.name] = main_category_data

        # Add the category total to the category_totals dictionary
        category_totals[main_category.name] = category_total

    return summary_table, category_totals
