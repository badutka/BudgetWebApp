from collections import defaultdict
from datetime import datetime
import pandas as pd

from django.shortcuts import get_object_or_404
from django.utils import timezone

from investments.models import Position, Instrument, Widget
from investments.services.valuation import portfolio_valuation, metrics
from investments.processing.portfolio_filters import PortfolioDetails
from investments.services.valuation.datetime_utils import standardize_datetime_by_period

from core.datastore import DataStore
from core.logger import logger


def setup_overview_widgets():
    portfolio_details = PortfolioDetails()

    account_type = 'ikze'
    widget_data = defaultdict(dict)
    widget_data['instruments'] = defaultdict(dict)

    instrument_types = ['ETF', 'ETC']
    currencies = ['PLN']
    taxes = ['Tax 19%']

    period = '1h'

    unique_symbols = (
        Position.objects
        .filter(account_type=account_type)
        .filter(instrument_type__in=instrument_types)
        .values_list('symbol', flat=True)
        .order_by('symbol')
        .distinct()
    )

    instrument_logos = dict(
        Instrument.objects
        .filter(symbol__in=unique_symbols)
        .values_list('symbol', 'logo_url')
    )

    for symbol in unique_symbols:
        instrument_pos = (
            portfolio_details
            .get_ops(type='open_pos')
            .get_acc_pos(account_type)
            .get_instrument_pos(symbol)
        )

        initial_value = instrument_pos.compute_purchase_value()
        profit = instrument_pos.compute_profit()
        hpr = metrics.Metric.HPR(initial_value, profit)

        widget_data['instruments'][symbol]['hpr'] = hpr
        widget_data['instruments'][symbol]['logo_url'] = instrument_logos.get(symbol)

    num_positions_opened_today = Position.objects.filter(
        account_type=account_type,
        instrument_type__in=instrument_types,
        open_time__date=timezone.localtime().date()
    ).count()

    current_value = portfolio_details.get_ops(type='open_pos').get_acc_pos(account_type).compute_current_value()
    profit = portfolio_details.get_ops(type='open_pos').get_acc_pos(account_type).compute_profit()
    free_funds = portfolio_details.get_ops(type='cash_ops').get_acc_pos(account_type).agg_deposit()

    widget_data['profit'] = profit
    widget_data['free_funds'] = free_funds
    widget_data['total_value'] = current_value + free_funds
    widget_data['allocation'] = 0.0713
    widget_data['new_today'] = num_positions_opened_today
    widget_data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")

    widget_data['labels']['num_unique_instruments'] = len(unique_symbols)
    widget_data['labels']['instrument_types'] = instrument_types
    widget_data['labels']['currencies'] = currencies
    widget_data['labels']['taxes'] = taxes

    positions = Position.objects.filter(
        account_type=account_type,
        instrument_type__in=instrument_types
    )
    # positions = positions[57:59]
    # logger.info(positions)
    positions_df = pd.DataFrame.from_records(positions.values('purchase_value', 'gross_pl', 'open_time'))
    positions_df['open_time'] = standardize_datetime_by_period(positions_df['open_time'], period)
    widget_data['metrics']['cagr'] = metrics.Metric.simple_cagr(positions_df, time_strat='min')
    widget_data['metrics']['wcagr'] = metrics.Metric.time_weighted_cagr(positions_df)

    portfolio_valuation.get_positions_value_over_time(positions, account_type, instrument_types, unique_symbols, period)
    df = DataStore(base_dir="../artifacts/portfolio_snapshots").load(f"portfolio_over_time_{account_type}", fmt='csv', prefix='')
    df = df.reset_index()
    widget_data['metrics']['twr'] = metrics.Metric.twr(df, time_period='total')

    widget_data['metrics_changes'] = {
        'D': metrics.Metric.twr(df, time_period='today'),
        'W': metrics.Metric.twr(df, time_period='last_week'),
        'M': metrics.Metric.twr(df, time_period='last_month'),
    }

    widget = get_object_or_404(Widget, id='28c2eaf5-ddde-4981-b88e-238cd6ef5419')

    widget.data = widget_data

    widget.save()
    logger.debug(f"Updated widget {widget.id} with new data ({len(widget_data)} items).")
