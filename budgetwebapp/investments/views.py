from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Position, Instrument, Dashboard
from budgetwebapp.investments import constants
from .processing import xtb_parser
from .services.valuation import market_data
from budgetwebapp.investments.services.valuation.portfolio_engine import PortfolioEngine
from django.http import JsonResponse
import json
from .models import BaseWidget

from core.logger import logger


def home_view(request):
    extract_dir = constants.XTB_DATA_EXTRACT_DIR
    xtb_parser.parse_data(extract_dir)

    positions = Position.objects.all()
    instruments = Instrument.objects.all()

    instrument_map = {i.symbol: i for i in instruments}

    for pos in positions:
        pos.instrument = instrument_map.get(pos.symbol)

    return render(request, 'investments/home.html', {
        'positions': positions
    })


def portfolio_view(request):
    dashboard_id = "e2293edc-1ecd-4fdb-9d75-ea1a58304acb"  # your dashboard UUID
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    # widgets = dashboard.dashboard_widgets.filter(widget_type='overview')
    widgets = list(dashboard.dashboard_widgets.filter(widget_type='overview'))

    # import time
    # start = time.perf_counter()
    market_data.ENTRY_POINT()
    engine = PortfolioEngine()
    engine.entry_point()

    refresh = 0
    for widget in widgets:
        logger.error('hello')
        widget.get_data(force_refresh=refresh)

    # for widget in widgets:
    #     widget.runtime_data = widget.get_data(force_refresh=refresh)

    context = {
        "widgets": widgets,
        'enable_account_details_visit': True,
        "dashboard": dashboard
    }

    return render(request, 'investments/portfolio.html', context)


def account_details(request, account_type):
    # todo: base widget data update on account id
    # account = Account.objects.filter(type=account_type).first()

    dashboard_id = "7c9d20c5-348a-4a2b-bad2-8483f45d54a6"  # your dashboard UUID
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    widgets = dashboard.dashboard_widgets.filter(config__account_type=account_type)

    # todo: a view of cash inflows where unique numbers are shown, so small inflows are also visible as auxillary
    # todo: a view of volume, and partial volume, sums of them, cases where 1.x was bought and also 0.x was bought.
    # todo: a view similar to instrument view on xtb, with number of open, list, etc. some stats. Clickable through overview logo?
    # todo: annual growth rates and drawdowns
    # todo: show gains split into fx rate gain and instrument gain

    # todo: drilldown modal in future -> GET /widget/<id>/series?resolution=none
    # todo: data source -> data model -> dashboard layer

    # todo: dashboard 3 dots -> edit, drilldown. on edit -> show editable field on side panel.
    # todo: when applying filters, on error push error message to frontend, continue with the rest of filters

    # todo: position view with details like earliest position wth loss (and date), same for latest

    # engine = PortfolioEngine()
    # engine.entry_point()

    # refresh = request.GET.get("refresh") == "1"

    # refresh = 0
    # for widget in widgets:
    #     widget.get_data(force_refresh=refresh)

    # for widget in widgets:
    #     # widget.update_widget_data()
    #     # widget.save()
    #     widget.runtime_data = widget.get_data(force_refresh=refresh)
    #     # data = get_widget_data(dashboard_widget)  # run this instead after refactor

    context = {
        'widgets': widgets,
        'dashboard': dashboard
    }

    return render(request, 'investments/account_details.html', context)


from collections import namedtuple

# Minimal widget object
Widget = namedtuple("Widget", ["id", "title", "row", "column", "width_units", "height_units"])


def dashboard_view(request, slug):
    dashboard = get_object_or_404(Dashboard, slug=slug)

    widgets = dashboard.dashboard_widgets.all()

    # Optional: filter logic
    account_type = request.GET.get('account_type')
    if account_type:
        widgets = widgets.filter(config__account_type=account_type)

    # Optional: run engine only for specific dashboards

    # market_data.ENTRY_POINT()

    if dashboard.slug == 'portfolio-overview':
        engine = PortfolioEngine()
        engine.entry_point()
        for widget in widgets:
            widget.get_data(force_refresh=0)

    context = {
        'widgets': widgets,
        'dashboard': dashboard,
        'enable_account_details_visit': dashboard.slug == 'portfolio-overview'
    }

    # return render(request, 'investments/dashboard.html', context)
    return render(request, 'investments/dashboard_new.html', context)


@require_POST
def update_widget_layout(request):
    data = json.loads(request.body)
    widgets = data.get("widgets", [])

    for w in widgets:
        try:
            widget = BaseWidget.objects.get(id=w["id"])
            widget.column = w["x"] + 1  # gridstack is 0-based
            widget.row = w["y"] + 1
            widget.width_units = w["w"]
            widget.height_units = w["h"]
            widget.save(update_fields=["column", "row", "width_units", "height_units"])
        except BaseWidget.DoesNotExist:
            continue

    return JsonResponse({"status": "ok"})
