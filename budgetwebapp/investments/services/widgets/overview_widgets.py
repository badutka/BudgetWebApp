from collections import defaultdict
from datetime import datetime
import pandas as pd

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum

from investments.models import Position, Instrument, Widget, CashOperation
from investments.services.valuation import portfolio_valuation, metrics
from investments.processing.portfolio_filters import PortfolioDetails
from investments.services.valuation.datetime_utils import standardize_datetime_by_period

from core.datastore import DataStore
from core.logger import logger


def setup_overview_widgets(widget_id: str):
    """
    Prepares and saves widget data for the given widget ID.
    """
    # --- Account-specific configuration ---
    CONFIGS = {
        "28c2eaf5-ddde-4981-b88e-238cd6ef5419": {
            "account_type": "main",
            "instrument_types": ["ETF", "ETC"],
            "currencies": ["PLN"],
            "taxes": ["Tax 19%"],
            "allocation": 0.0713,
            "progress": {},
        },
        "d31b59cb-1e90-459d-8767-008603ec0e2d": {
            "account_type": "ike",
            "instrument_types": ["ETF", "ETC"],
            "currencies": ["PLN"],
            "taxes": ["Tax 0%"],
            "allocation": 0.10,
            "progress": {
                'limit': 26019
            },
        },
        "2579b88e-dc7f-4c89-8bc3-1b44680f6d81": {
            "account_type": "ikze",
            "instrument_types": ["ETF", "ETC"],
            "currencies": ["PLN"],
            "taxes": ["Tax 10%"],
            "allocation": 0.10,
            "progress": {
                'limit': 10407.60
            },
        },
    }

    config = CONFIGS.get(widget_id)
    if not config:
        raise ValueError(f"No configuration found for widget_id {widget_id}")

    # --- Gather data ---
    widget_data = _gather_portfolio_data(**config)

    # --- Persist widget data ---
    widget = get_object_or_404(Widget, id=widget_id)
    widget.data = widget_data
    widget.save()
    logger.info(f"Updated widget {widget.id} with new data ({len(widget_data)} items).")


def _gather_portfolio_data(account_type: str, instrument_types: list, currencies: list,
                           taxes: list, allocation: float, progress: dict) -> dict:
    portfolio_details = PortfolioDetails()
    widget_data = defaultdict(dict)
    widget_data['instruments'] = defaultdict(dict)

    period = '1h'

    # --- Core data queries ---
    unique_symbols = (
        Position.objects
        .filter(account_type=account_type, instrument_type__in=instrument_types)
        .values_list('symbol', flat=True)
        .order_by('symbol')
        .distinct()
    )

    instrument_logos = dict(
        Instrument.objects
        .filter(symbol__in=unique_symbols)
        .values_list('symbol', 'logo_url')
    )

    num_positions_opened_today = Position.objects.filter(
        account_type=account_type,
        instrument_type__in=instrument_types,
        open_time__date=timezone.localtime().date()
    ).count()

    # --- Portfolio-level metrics ---
    portfolio_value_over_time = portfolio_valuation.get_positions_value_over_time(
        Position.objects.filter(account_type=account_type, instrument_type__in=instrument_types),
        account_type, unique_symbols, period
    )

    df_portfolio_over_time, df_positions_cagr, instruments_value_pln, tickers_input_value, tickers_total_value = portfolio_value_over_time
    df_portfolio_over_time = df_portfolio_over_time.reset_index()

    # --- Populate main metrics ---
    widget_data['allocation'] = allocation
    if progress:
        widget_data['progress_current'] = \
        CashOperation.objects.filter(account_type=account_type, type=f'{account_type.upper()} Deposit').aggregate(
            total=Sum('amount'))['total'] or 0
        widget_data['progress_limit'] = progress['limit']
        widget_data['progress_pct'] = widget_data['progress_current'] / widget_data['progress_limit']

    widget_data['new_today'] = num_positions_opened_today
    widget_data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")

    widget_data['labels']['num_unique_instruments'] = len(unique_symbols)
    widget_data['labels']['instrument_types'] = instrument_types
    widget_data['labels']['currencies'] = currencies
    widget_data['labels']['taxes'] = taxes

    # --- Portfolio valuation metrics ---
    widget_data['total_value'] = df_portfolio_over_time['total_portfolio_value'].iloc[-1]
    widget_data['profit'] = tickers_total_value.sum() - tickers_input_value.sum()
    widget_data['free_funds'] = df_portfolio_over_time['free_funds'].iloc[-1]

    # --- Per-instrument metrics ---
    for ticker in unique_symbols:
        hpr = metrics.Metric.HPR(
            tickers_input_value[ticker] * (1 / 0.995),
            tickers_total_value[ticker]
        )
        widget_data['instruments'][ticker]['hpr'] = hpr
        widget_data['instruments'][ticker]['logo_url'] = instrument_logos.get(ticker)

    # --- Summary metrics ---
    widget_data['metrics']['cagr'] = metrics.Metric.new_cagr(df_portfolio_over_time)
    widget_data['metrics']['wcagr'] = metrics.Metric.new_weighted_cagr(df_positions_cagr)
    widget_data['metrics']['twr'] = metrics.Metric.twr(df_portfolio_over_time, time_period='total')

    widget_data['metrics_changes'] = {
        'D': metrics.Metric.twr(df_portfolio_over_time, time_period='today'),
        'W': metrics.Metric.twr(df_portfolio_over_time, time_period='last_week'),
        'M': metrics.Metric.twr(df_portfolio_over_time, time_period='last_month'),
    }

    return widget_data

# def setup_overview_widgets():
#     portfolio_details = PortfolioDetails()
#
#     account_type = 'main'
#     widget_data = defaultdict(dict)
#     widget_data['instruments'] = defaultdict(dict)
#
#     instrument_types = ['ETF', 'ETC']
#     currencies = ['PLN']
#     taxes = ['Tax 19%']
#
#     period = '1h'
#
#     unique_symbols = (
#         Position.objects
#         .filter(account_type=account_type)
#         .filter(instrument_type__in=instrument_types)
#         .values_list('symbol', flat=True)
#         .order_by('symbol')
#         .distinct()
#     )
#
#     instrument_logos = dict(
#         Instrument.objects
#         .filter(symbol__in=unique_symbols)
#         .values_list('symbol', 'logo_url')
#     )
#
#     num_positions_opened_today = Position.objects.filter(
#         account_type=account_type,
#         instrument_type__in=instrument_types,
#         open_time__date=timezone.localtime().date()
#     ).count()
#
#     current_value = portfolio_details.get_ops(type='open_pos').get_acc_pos(account_type).compute_current_value()
#     profit = portfolio_details.get_ops(type='open_pos').get_acc_pos(account_type).compute_profit()
#     free_funds = portfolio_details.get_ops(type='cash_ops').get_acc_pos(account_type).agg_deposit()
#
#     # widget_data['profit'] = profit
#     # widget_data['free_funds'] = free_funds
#     # widget_data['total_value'] = current_value + free_funds
#     widget_data['allocation'] = 0.0713
#     widget_data['progress'] = 0.2
#     widget_data['new_today'] = num_positions_opened_today
#     widget_data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M")
#
#     widget_data['labels']['num_unique_instruments'] = len(unique_symbols)
#     widget_data['labels']['instrument_types'] = instrument_types
#     widget_data['labels']['currencies'] = currencies
#     widget_data['labels']['taxes'] = taxes
#
#     positions = Position.objects.filter(
#         account_type=account_type,
#         instrument_type__in=instrument_types
#     )
#     # positions = positions[57:59]
#     # logger.info(positions)
#     positions_df = pd.DataFrame.from_records(positions.values('purchase_value', 'gross_pl', 'open_time'))
#     positions_df['open_time'] = standardize_datetime_by_period(positions_df['open_time'], period)
#     # widget_data['metrics']['cagr'] = metrics.Metric.simple_cagr(positions_df, time_strat='min')
#
#     portfolio_value_over_time = portfolio_valuation.get_positions_value_over_time(positions, account_type,
#                                                                                   unique_symbols, period)
#     (df_portfolio_over_time, df_positions_cagr, instruments_value_pln, tickers_input_value, tickers_total_value) = portfolio_value_over_time
#     # df_portfolio_over_time = DataStore(base_dir="../artifacts/portfolio_snapshots").load(f"portfolio_over_time_{account_type}", fmt='csv', prefix='')
#     df_portfolio_over_time = df_portfolio_over_time.reset_index()
#
#     widget_data['total_value'] = df_portfolio_over_time['total_portfolio_value'].iloc[-1]
#     widget_data['profit'] = tickers_total_value.sum() - tickers_input_value.sum()
#     widget_data['free_funds'] = df_portfolio_over_time['free_funds'].iloc[-1]
#
#     for ticker in unique_symbols:
#         instrument_pos = (
#             portfolio_details
#             .get_ops(type='open_pos')
#             .get_acc_pos(account_type)
#             .get_instrument_pos(ticker)
#         )
#
#         # Input is calculated via yfinance data, adjusting is required in order to match XTB's HPRs
#         # tickers_total_value[ticker] * (1/0.995) <- scales input to cover 0.05% margin in BUY direction
#         # todo: determine if scaling at more granular level impacts results
#         hpr = metrics.Metric.HPR(tickers_input_value[ticker] * (1 / 0.995), tickers_total_value[ticker])
#
#         widget_data['instruments'][ticker]['hpr'] = hpr
#         widget_data['instruments'][ticker]['logo_url'] = instrument_logos.get(ticker)
#
#     widget_data['metrics']['cagr'] = metrics.Metric.new_cagr(df_portfolio_over_time)
#     widget_data['metrics']['wcagr'] = metrics.Metric.new_weighted_cagr(df_positions_cagr)
#     widget_data['metrics']['twr'] = metrics.Metric.twr(df_portfolio_over_time, time_period='total')
#
#     widget_data['metrics_changes'] = {
#         'D': metrics.Metric.twr(df_portfolio_over_time, time_period='today'),
#         'W': metrics.Metric.twr(df_portfolio_over_time, time_period='last_week'),
#         'M': metrics.Metric.twr(df_portfolio_over_time, time_period='last_month'),
#     }
#
#     widget = get_object_or_404(Widget, id='28c2eaf5-ddde-4981-b88e-238cd6ef5419')
#
#     widget.data = widget_data
#
#     widget.save()
#     logger.info(f"Updated widget {widget.id} with new data ({len(widget_data)} items).")
#
#
# def test_cagr():
#     # CNDX.UK
#     test_data = {
#         "holding_years": [1.174538, 1.174538, 1.190965],
#         "open_time": [
#             datetime(2024, 8, 20, 15, 00),
#             datetime(2024, 8, 20, 9, 30),
#             datetime(2024, 8, 14, 16, 36)
#         ],
#         "purchase_value": [500.07, 500.34, 500.36],
#         "open_price_total_pln": [500.07, 500.34, 500.36],
#         "gross_pl": [91.68, 87.8, 114.09]
#     }
#     test_data = pd.DataFrame(test_data)
#     logger.debug(test_data)
#     test_wcagr = metrics.Metric.time_weighted_cagr(test_data)
#     logger.debug(f'{test_wcagr = }')
#     test_new_wcagr = metrics.Metric.new_weighted_cagr(test_data)
#     logger.debug(f'{test_new_wcagr = }')
#     # test_wcagr = np.float64(0.16346659984699974)
#
#     # df = df_positions_cagr[
#     #     (df_positions_cagr.index.isin(['2024-08-14 17:00:00', '2024-08-20 16:00:00', '2024-08-20 17:00:00']))]
