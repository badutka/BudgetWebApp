from django.shortcuts import render, redirect
from core import utils

from core.summaries import monthly_summary, monthly_summary_detailed

def monthly_summary_detailed_view(request):
    if request.method == 'GET':
        params = utils.flatten_querydict(request.GET)

        all_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, None)
        years = monthly_summary.get_available_years(all_summaries)
        year = request.GET.get('year', years)

        if 'year' not in request.GET and years:
            return redirect(f"{request.path}?year={years[-1]}")

        parent_categories = utils.fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)
        monthly_parent_category_summaries = utils.fetch_api_and_get_response(request,'budget:monthly_parent_category_summaries', 200, params)
        monthly_category_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_category_summaries', 200, params)

        parent_categories_filtered = monthly_summary_detailed.get_filtered_parent_categories(request, parent_categories)

        summary = monthly_summary_detailed.get_summary_detailed(parent_categories_filtered, monthly_parent_category_summaries, monthly_category_summaries, 'expense')
        # todo: filter no-cat parent, filter 0-totals parent

        context = {
            'year': year,
            'years': years,
            'parent_categories': parent_categories,
            'summary': summary
        }

        if request.headers.get('HX-Request'):
            return render(request, 'budget/summary/monthly_summary_detailed_table.html', context)

    return render(request, 'budget/summary/monthly_summary_detailed.html', context)


def monthly_summary_view(request):
    if request.method == 'GET':
        params = utils.flatten_querydict(request.GET)

        all_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, None)
        years = monthly_summary.get_available_years(all_summaries)
        year = request.GET.get('year', years)

        if 'year' not in request.GET and years:
            return redirect(f"{request.path}?year={years[-1]}")

        # --- Fetch parent category summaries ---
        monthly_parent_category_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_parent_category_summaries', 200, params)
        monthly_summaries = utils.fetch_api_and_get_response(request, 'budget:monthly_summaries', 200, params)

        # --- Pass API data to helpers ---
        incoming_rows, outgoing_rows = monthly_summary.get_parent_category_monthly_totals_rows(monthly_parent_category_summaries)

        if 'parent_category' in request.GET:
            starting_balance = monthly_summary.get_starting_balance(request, year)
            totals = monthly_summary.build_totals_rows(incoming_rows, outgoing_rows, starting_balance=starting_balance)
        else:
            totals = monthly_summary.get_totals_rows(monthly_summaries)

        parent_categories = utils.fetch_api_and_get_response(request, 'budget:parent_categories', 200, params)

        context = {
            'totals': totals,
            'incoming_rows': incoming_rows,
            'outgoing_rows': outgoing_rows,
            'year': year,
            'years': years,
            'parent_categories': parent_categories
        }

        if request.headers.get('HX-Request'):
            return render(request, 'budget/summary/monthly_summary_table.html', context)

    return render(request, 'budget/summary/monthly_summary.html', context)