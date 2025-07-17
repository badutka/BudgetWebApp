from collections import defaultdict, namedtuple
from typing import Any

from django.http import HttpRequest

from core.utils import fetch_api_and_get_response

MonthlySummaryRow = namedtuple('MonthlySummaryRow', ['name', 'amounts'])


def get_parent_category_monthly_totals_rows(
        data: list[dict[str, Any]]
) -> tuple[list[MonthlySummaryRow], list[MonthlySummaryRow]]:
    """
    Aggregates income and expense totals by parent category across 12 months.

    Args:
        data: List of transaction dicts with:
              'month', 'transaction_type', 'parent_category_name', and 'amount'.

    Returns:
        Tuple of two lists of MonthlySummaryRow:
          - First for income rows
          - Second for expense rows
    """
    income_totals = defaultdict(lambda: [0.0] * 12)
    expense_totals = defaultdict(lambda: [0.0] * 12)

    for s in data:
        idx = s['month'] - 1
        if s['transaction_type'] == 'INCOMING':
            income_totals[s['parent_category_name']][idx] += float(s['amount'])
        elif s['transaction_type'] == 'OUTGOING':
            expense_totals[s['parent_category_name']][idx] += float(s['amount'])

    def build_rows(source_dict: dict[str, list[float]]) -> list[MonthlySummaryRow]:
        rows = []
        for parent_name in sorted(source_dict.keys()):
            vals = source_dict[parent_name]
            rows.append(MonthlySummaryRow(name=parent_name, amounts=vals + [sum(vals)]))
        return rows

    return build_rows(income_totals), build_rows(expense_totals)


def get_starting_balance(request: HttpRequest, year: int) -> float:
    """
    Retrieves the starting balance for a given year.

    Logic:
    - First attempts to fetch December's ending balance from the previous year.
    - If unavailable, falls back to summing starting balances of all money accounts.

    Args:
        request: Django request object used for making internal API calls.
        year: The current year for which we want to determine the starting balance.

    Returns:
        Starting balance as a float.
    """
    # Try to fetch the monthly summary for December of the previous year
    previous_summary = fetch_api_and_get_response(
        request,
        'budget:monthly_summaries',
        200,
        args=[int(year) - 1, 12]
    )

    if previous_summary:
        # If the summary exists, return its ending balance as the starting balance for the new year
        return float(previous_summary[0]['ending_balance'])
    else:
        # If no previous summary exists (e.g., first time setup),
        # fall back to the initial starting balances of all money accounts
        money_accounts = fetch_api_and_get_response(
            request,
            'budget:money_accounts',
            200)
        return sum([float(account['starting_balance']) for account in money_accounts])


def get_totals_rows(data: list[dict[str, Any]]) -> list[MonthlySummaryRow]:
    """
    Aggregates total monthly values for income, expenses, net savings, and ending balance.

    Args:
        data: List of dicts each containing:
              'month', 'income', 'expenses', 'net_savings', and 'ending_balance'.

    Returns:
        A list of 4 MonthlySummaryRow namedtuples each with 'name' and 'amounts' (13 floats: 12 months + total).
    """
    income = [0.0] * 12
    expenses = [0.0] * 12
    net_savings = [0.0] * 12
    ending_balance = [0.0] * 12

    for s in data:
        idx = s['month'] - 1
        income[idx] = float(s['income'])
        expenses[idx] = float(s['expenses'])
        net_savings[idx] = float(s['net_savings'])
        ending_balance[idx] = float(s['ending_balance'])

    return [
        MonthlySummaryRow(name='Income', amounts=income + [sum(income)]),
        MonthlySummaryRow(name='Expenses', amounts=expenses + [sum(expenses)]),
        MonthlySummaryRow(name='Net Savings', amounts=net_savings + [sum(net_savings)]),
        MonthlySummaryRow(
            name='Ending Balance',
            amounts=ending_balance + [ending_balance[-1] if any(ending_balance) else 0.0],
        ),
    ]


def build_totals_rows(
        income_rows: list[MonthlySummaryRow],
        expense_rows: list[MonthlySummaryRow],
        starting_balance: float = 0.0
) -> list[MonthlySummaryRow]:
    """
    Computes total income, expenses, net savings, and ending balance from row data.

    Args:
        income_rows: List of income rows, each with 13 monthly values.
        expense_rows: List of expense rows, each with 13 monthly values.
        starting_balance: Optional float to seed the ending balance.

    Returns:
        List of 4 MonthlySummaryRow namedtuples with 'name' and 'amounts' fields.
    """

    def sum_vertically(rows: list[MonthlySummaryRow]) -> list[float]:
        totals = [0.0] * 13
        for row in rows:
            for i in range(13):
                totals[i] += row.amounts[i]
        return totals

    income_total = sum_vertically(income_rows)
    expense_total = sum_vertically(expense_rows)

    net_savings = [income_total[i] - expense_total[i] for i in range(12)]
    net_savings.append(sum(net_savings))

    # Compute ending balance month by month
    ending_balance = []
    running_balance = starting_balance
    for ns in net_savings[:12]:
        running_balance += ns
        ending_balance.append(running_balance)
    ending_balance.append(running_balance)

    return [
        MonthlySummaryRow(name='Income', amounts=income_total),
        MonthlySummaryRow(name='Expenses', amounts=expense_total),
        MonthlySummaryRow(name='Net Savings', amounts=net_savings),
        MonthlySummaryRow(name='Ending Balance', amounts=ending_balance),
    ]


def get_available_years(monthly_summaries: list[dict[str, Any]]) -> list[int]:
    """
    Extracts all unique years from the data, sorted in descending order.

    Args:
        monthly_summaries: List of dicts, each with a 'year' key.

    Returns:
        List of unique years, sorted descending.
    """
    return sorted({s['year'] for s in monthly_summaries}, reverse=True)