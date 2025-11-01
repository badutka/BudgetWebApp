from django.shortcuts import render, get_object_or_404

from .models import Position, Instrument, Dashboard, OverviewWidget, DashboardWidget, ChartWidget
from .processing import xtb_parser
from .services.valuation import market_data


def home_view(request):
    xtb_parser.parse_data()
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

    # Fetch all DashboardWidget instances for this dashboard
    # dashboard_widgets = dashboard.dashboard_widgets.select_related('widget_content_type').all()
    dashboard_widgets = dashboard.get_widgets()

    # market_data.ENTRY_POINT()

    # Update data for each widget
    for dw in dashboard_widgets:
        dw.widget.update_widget_data()
        dw.widget.save()  # if you want to persist updates

    context = {
        "dashboard_widgets": dashboard_widgets,
        'enable_account_details_visit': True
    }

    return render(request, 'investments/portfolio.html', context)


def account_details(request, widget_id):
    widget = get_object_or_404(OverviewWidget, id=widget_id)
    widget2 = get_object_or_404(ChartWidget, id='558dd3e7-2cd7-4a04-b923-06ab8103e9f5')
    temp_dw = DashboardWidget(
        widget=widget,
        row=1, column=1, width_units=3, height_units=8
    )
    temp_dw2 = DashboardWidget(
        widget=widget2,
        row=1, column=4, width_units=4, height_units=8
    )

    temp_dw3 = DashboardWidget(
        row=1, column=3, width_units=2, height_units=8
    )

    context = {
        'dashboard_widget': temp_dw,
        'widget': temp_dw.widget,
        'dw2': temp_dw2,
        'chart2': temp_dw2.widget
    }


    return render(request, 'investments/account_details.html', context)
