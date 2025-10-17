from django.shortcuts import render

from .models import Position, Instrument
from investments.processing import xtb_parser


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
