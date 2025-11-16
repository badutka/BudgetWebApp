from django.shortcuts import render, get_object_or_404

from .models import Position, Instrument, Dashboard, OverviewWidget, DashboardWidget, ChartWidget, Account
from investments.services.widgets.registry import get_widget_logic
from .processing import xtb_parser
from .services.valuation import market_data
from core.datastore import DataStore


def home_view(request):
    # xtb_parser.parse_data()
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
    dashboard_widgets = dashboard.dashboard_widgets.filter(widget__widget_type='overview')

    # market_data.ENTRY_POINT()

    for dw in dashboard_widgets:
        dw.widget.update_widget_data()
        dw.widget.save()

    for dw in dashboard_widgets:
        widget = dw.widget
        logic_cls = get_widget_logic(widget.widget_type, getattr(widget, "chart_subtype", None))
        if not logic_cls:
            continue

        logic = logic_cls(widget)
        if hasattr(logic, "update_allocation"):
            logic.update_allocation()
            widget.save(update_fields=["data"])

    context = {
        "dashboard_widgets": dashboard_widgets,
        'enable_account_details_visit': True
    }

    return render(request, 'investments/portfolio.html', context)


def account_details(request, account_type):
    # todo: base widget data update on account id
    # account = Account.objects.filter(type=account_type).first()

    dashboard_id = "7c9d20c5-348a-4a2b-bad2-8483f45d54a6"  # your dashboard UUID
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    dashboard_widgets = dashboard.dashboard_widgets.filter(widget__config__account_type=account_type)

    print(dashboard_widgets)

    for dw in dashboard_widgets:
        print(dw.widget)
        dw.widget.update_widget_data()
        dw.widget.save()

    context = {
        'dashboard_widgets': dashboard_widgets
    }

    return render(request, 'investments/account_details.html', context)
