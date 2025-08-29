from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.http import HttpRequest

from budget.services.dashboard_filters import DashboardFilters
from budget.services.kpis import get_kpis
from budget.services.data_fetcher import fetch_categories_and_summaries
from core.dashboard_data import charts

from core.logger import logger

@require_http_methods(["GET", "POST"])
def chart_summary(request: HttpRequest):
    dashboard_filters = DashboardFilters(request)
    # todo: check if persisting dsb_row_filter k:v in filter row is redundant
    logger.warn(request.GET)
    logger.info(dashboard_filters.rows)

    row_filter_name = request.POST.get("dsb_row_filter") or request.GET.get("dsb_row_filter")
    # Get previous submitted rows from URL or POST
    submitted_rows = request.POST.getlist("submitted") or request.GET.getlist("submitted")
    # Append current row if not already in the list
    if row_filter_name and row_filter_name not in submitted_rows:
        submitted_rows.append(row_filter_name)
    logger.debug(f'{submitted_rows = }')

    cards_row_filters = dashboard_filters.get_row("cards_row")
    summary_row_filters = dashboard_filters.get_row("summary_row")

    # ------------------------------
    # HTMX partial updates
    # ------------------------------
    if dashboard_filters.is_htmx:
        # Row-specific filters
        row_filters = dashboard_filters.get_row(row_filter_name)

        if row_filter_name == "cards_row" and row_filters:
            kpis = get_kpis(dashboard_filters)
            context = {
                "kpis": kpis[0],
                "date_range": kpis[1],
                "submitted_rows": submitted_rows
            }
            return render(request, "budget/dashboard/dashboard_cards_partial.html", context)

        elif row_filter_name == "summary_row" and row_filters:
            summary_data = charts.calculate_chart_data(summary_row_filters)
            context = {
                "summary_data": summary_data,
                "submitted_rows": submitted_rows
            }
            return render(request, "budget/dashboard/dsb_summary_charts_partial.html", context)

    # ------------------------------
    # Full page load
    # ------------------------------
    monthly_summaries, parent_categories, categories = fetch_categories_and_summaries(request)
    summary_data = charts.calculate_chart_data(summary_row_filters)
    kpis = get_kpis(dashboard_filters)

    context = {
        "summary_data": summary_data,
        "kpis": kpis[0],
        "date_range": kpis[1],
        "parent_categories": parent_categories,
        "categories": categories,
        "transaction_types": ["OUTGOING", "INNER", "INCOMING"],
        "periods": ["day", "month", "year", "all_time"],
        "cards_row_filters": dashboard_filters.get_row("cards_row"),
        "summary_row_filters": dashboard_filters.get_row("summary_row"),
        "years": list(range(2023, 2031)),
        "submitted_rows": submitted_rows,
    }

    return render(request, "budget/dashboard/chart_summary.html", context)


def dashboard_card_modal_view(request):
    card_type = request.GET.get("type")
    context = {
        'card_type': card_type
    }
    return render(request, 'budget/dashboard/dashboard_card_modal.html', context)
