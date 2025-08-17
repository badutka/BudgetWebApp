from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.http import HttpRequest

from budget.services.dashboard_filters import DashboardFilters
from budget.services.kpis import get_kpis
from budget.services.data_fetcher import fetch_categories_and_summaries

@require_http_methods(["GET", "POST"])
def chart_summary(request: HttpRequest):
    """
    Render the dashboard chart summary page or HTMX partials.

    Behavior:
        - Standard GET:
            Full page render with KPIs, categories, and summaries.
        - HTMX GET (filter submission):
            Partial update of KPI cards based on selected filters.
        - HTMX POST (refresh button):
            Recalculates KPIs if requested, then updates KPI cards.

    Args:
        request (HttpRequest): The Django request object.

    Returns:
        HttpResponse: Rendered HTML page or partial fragment.
    """
    filters = DashboardFilters(request)

    # ------------------------------
    # HTMX partial update for KPI cards
    # ------------------------------
    if filters.is_htmx and filters.dsb_row_filter == "cards_row":
        kpis = get_kpis(filters)
        context = {
            "kpis": kpis[0],
            "date_range": kpis[1],
        }
        return render(request, "budget/dashboard/dashboard_cards_partial.html", context)

    # ------------------------------
    # Full page load
    # ------------------------------
    monthly_summaries, parent_categories, categories = fetch_categories_and_summaries(request, filters)
    kpis = get_kpis(filters)

    context = {
        "monthly_data": monthly_summaries,
        "kpis": kpis[0],
        "date_range": kpis[1],
        "parent_categories": parent_categories,
        "categories": categories,
        "transaction_types": ["OUTGOING", "INNER", "INCOMING"],
        "periods": ["day", "month", "year", "all_time"],
        "date_for": filters.date_for,
        "date_from": filters.date_from,
        "date_to": filters.date_to,
        "aggregation": filters.aggregation,
        "years": list(range(2023, 2031)),
    }

    return render(request, "budget/dashboard/chart_summary.html", context)

def dashboard_card_modal_view(request):
    card_type = request.GET.get("type")
    context = {
        'card_type': card_type
    }
    return render(request, 'budget/dashboard/dashboard_card_modal.html', context)
