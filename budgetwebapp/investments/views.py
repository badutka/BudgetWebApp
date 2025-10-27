from django.shortcuts import render, get_object_or_404

from .models import Position, Instrument, Dashboard, OverviewWidget
from .services.valuation import market_data

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
    widgets = {str(w.id): w for w in dashboard.base_widgets.all()}

    context = {"widgets": widgets}

    # market_data.ENTRY_POINT()
    for widget in widgets.values():
        # if widget.config.get('account_type') == 'main':
        widget.save()

    return render(request, 'investments/portfolio.html', context)
