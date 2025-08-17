from django.http import HttpResponseNotAllowed
from django.views.decorators.http import require_http_methods
from django.shortcuts import render

from core import utils
from core.dashboard import kpi_saving, kpi_reading, filters as dsb_filters
from core.logger import logger


@require_http_methods(["GET", "POST"])
def chart_summary(request):
    years = list(range(2023, 2031))  # 2030 inclusive

    is_htmx = request.headers.get('HX-Request') is not None
    refresh_kpis = False

    # Determine filters depending on request type
    if is_htmx and request.method == "POST":
        # HTMX POST for refresh button
        dsb_row_filter = request.POST.get('dsb_row_filter')
        refresh_kpis = request.POST.get('cards_row_refresh') == "true"
        # Include current filter values from the form
        query_data = request.POST
    else:
        # GET request (page load or filter form submission)
        dsb_row_filter = request.GET.get('dsb_row_filter')
        query_data = request.GET

    logger.debug(f'{request.method = }')
    logger.debug(f'{query_data = }')

    # Read filter parameters
    cards_row_transaction_types = dsb_filters.get_dsb_filter_param_or_none(query_data, 'cards_row_transaction_type')
    cards_row_parent_category = dsb_filters.get_dsb_filter_param_or_none(query_data, 'cards_row_parent_category')
    cards_row_category = dsb_filters.get_dsb_filter_param_or_none(query_data, 'cards_row_category')

    # Map category IDs to names
    cards_row_parent_category = dsb_filters.get_parent_categories_names_list(cards_row_parent_category)
    cards_row_category = dsb_filters.get_categories_names_list(cards_row_category)
    apply_filters = dsb_filters.not_none_filters((cards_row_category, cards_row_parent_category, cards_row_transaction_types))

    # Aggregation and date handling
    aggregation = query_data.get('cards_row_aggregation', 'month')
    date_for = query_data.get('cards_row_date_for')
    date_for = dsb_filters.parse_date(date_for, mode=aggregation) if aggregation != 'all_time' else None

    date_from = query_data.get('cards_row_date_from') or None
    date_to = query_data.get('cards_row_date_to') or None
    apply_date_filters = dsb_filters.not_none_filters((date_from, date_to))

    # ------------------------------
    # HTMX partial update for summary cards
    # ------------------------------
    if is_htmx and dsb_row_filter == "cards_row":
        if refresh_kpis:
            logger.debug('Recalculating KPIs')
            kpi_saving.calculate_daily_kpis()

        kpis = kpi_reading.get_kpis(
            aggregation, date_for, date_from, date_to,
            apply_date_filters, apply_filters,
            cards_row_transaction_types, cards_row_parent_category, cards_row_category
        )
        context = {
            'kpis': kpis[0],
            'date_range': kpis[1],
        }
        return render(request, 'budget/dashboard/dashboard_cards_partial.html', context)

    # ------------------------------
    # Full page load or filter submission
    # ------------------------------
    params = utils.flatten_querydict(query_data)
    monthly_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, [('year', '2025')])
    parent_categories = utils.fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)
    categories = utils.fetch_api_and_get_response(request, 'budget:categories', 200, params)

    kpis = kpi_reading.get_kpis(
        aggregation, date_for, date_from, date_to,
        apply_date_filters, apply_filters,
        cards_row_transaction_types, cards_row_parent_category, cards_row_category
    )

    context = {
        'monthly_data': monthly_summaries,
        'kpis': kpis[0],
        'date_range': kpis[1],
        'parent_categories': parent_categories,
        'categories': categories,
        'transaction_types': ['OUTGOING', 'INNER', 'INCOMING'],
        'periods': ["day", "month", "year", "all_time"],
        'date_for': date_for,
        'date_from': date_from,
        'date_to': date_to,
        'years': years,
        'aggregation': aggregation,
    }

    return render(request, 'budget/dashboard/chart_summary.html', context)


def dashboard_card_modal_view(request):
    card_type = request.GET.get("type")
    context = {
        'card_type': card_type
    }
    return render(request, 'budget/dashboard/dashboard_card_modal.html', context)
