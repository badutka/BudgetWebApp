from django.http import HttpResponseNotAllowed
from django.shortcuts import render

from core import utils
from core.dashboard import kpi_saving, kpi_reading, filters as dsb_filters
from core.logger import logger

def chart_summary(request):
    years = list(range(2023, 2031))  # 2030 inclusive
    dsb_row_filter = request.GET.get('dsb_row_filter')
    is_htmx = request.headers.get('HX-Request') is not None

    cards_row_transaction_types = dsb_filters.get_dsb_filter_param_or_none(request.GET, 'cards_row_transaction_type')
    cards_row_parent_category = dsb_filters.get_dsb_filter_param_or_none(request.GET, 'cards_row_parent_category')
    cards_row_category = dsb_filters.get_dsb_filter_param_or_none(request.GET, 'cards_row_category')

    # Apply category name mapping here so get_kpis doesn't have to know about it
    cards_row_parent_category = dsb_filters.get_parent_categories_names_list(cards_row_parent_category)
    cards_row_category = dsb_filters.get_categories_names_list(cards_row_category)

    apply_filters = dsb_filters.not_none_filters((cards_row_category, cards_row_parent_category, cards_row_transaction_types))

    aggregation = request.GET.get('cards_row_aggregation')
    aggregation = 'month' if not aggregation else aggregation

    date_for = request.GET.get('cards_row_date_for')
    date_for = dsb_filters.parse_date(date_for, mode=aggregation) if aggregation != 'all_time' else None
    logger.debug(f'{date_for = }')

    if is_htmx and dsb_row_filter == "cards_row":

        kpis = kpi_reading.get_kpis(aggregation, date_for, apply_filters, cards_row_transaction_types, cards_row_parent_category, cards_row_category)
        context = {
            'kpis': kpis[0],
            'date_range': kpis[1],
        }

        return render(request, 'budget/dashboard/dashboard_cards_partial.html', context)

    elif request.method == 'GET':
        params = utils.flatten_querydict(request.GET)

        monthly_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, [('year', '2025')])
        parent_categories = utils.fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)
        categories = utils.fetch_api_and_get_response(request, 'budget:categories', 200, params)

        kpi_saving.calculate_daily_kpis()
        # kpis = kpi_reading.get_kpis('day', '04.07.2025')
        kpis = kpi_reading.get_kpis(aggregation, date_for, apply_filters, cards_row_transaction_types, cards_row_parent_category, cards_row_category)
        # kpis = kpi_reading.get_kpis('year', '2025')
        # kpis = kpi_reading.get_kpis('all')
        # todo: when first month/year of all time, then change = N/A -> for now handled in template to be 0

        context = {
            'monthly_data': monthly_summaries,
            'kpis': kpis[0],
            'date_range': kpis[1],
            'parent_categories': parent_categories,
            'categories': categories,
            'transaction_types': ['OUTGOING', 'INNER', 'INCOMING'],
            'periods': ["day", "month", "year", "all_time"],
            'date_for': date_for,
            'years': years,
            'aggregation': aggregation
        }

        return render(request, 'budget/dashboard/chart_summary.html', context)


    # Log the unexpected method
    logger.warning(f"Unsupported method {request.method} on chart_summary view")

    # Explicitly handle other cases, e.g. method not allowed
    return HttpResponseNotAllowed(['GET'])


def dashboard_card_modal_view(request):
    card_type = request.GET.get("type")
    context = {
        'card_type': card_type
    }
    return render(request, 'budget/dashboard/dashboard_card_modal.html', context)
