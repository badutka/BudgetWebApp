import os
from collections import defaultdict
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

from django.db.models import Sum
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from investments.models import Position, CashOperation, Instrument, Widget
from investments.processing import metrics

from core.logger import logger


def setup_overview_widget():
    portfolio_details = PortfolioDetails()

    account_type = 'main'
    widget_data = defaultdict(dict)
    widget_data['instruments'] = defaultdict(dict)

    instrument_types = ['ETF', 'ETC']
    currencies = ['PLN']
    taxes = ['Tax 19%']

    period = '1d'

    # Step 1: Get all unique symbols from positions
    unique_symbols = (
        Position.objects
        .filter(account_type=account_type)
        .filter(instrument_type__in=instrument_types)
        .values_list('symbol', flat=True)
        .order_by('symbol')
        .distinct()
    )

    # Step 2: Build a mapping of {symbol: logo_url} from Instruments
    instrument_logos = dict(
        Instrument.objects
        .filter(symbol__in=unique_symbols)
        .values_list('symbol', 'logo_url')
    )

    # Step 3: Compute metrics and attach logo_url
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
    wcagr = metrics.Metric.time_weighted_cagr(positions)
    cagr = metrics.Metric.simple_cagr(positions)

    widget_data['metrics']['cagr'] = cagr
    widget_data['metrics']['wcagr'] = wcagr

    # get_positions_value_over_time(account_type, instrument_types, unique_symbols)
    get_positions_value_over_time(account_type, instrument_types, unique_symbols, period)

    # Step 4: Fetch the widget instance
    widget = get_object_or_404(Widget, id='28c2eaf5-ddde-4981-b88e-238cd6ef5419')

    # Step 5: Assign widget_data (dict) to the data field
    widget.data = widget_data

    # Step 6 :Save it
    widget.save()
    logger.debug(f"Updated widget {widget.id} with new data ({len(widget_data)} items).")


def get_positions_value_over_time(account_type, instrument_types, tickers, period):
    TICKER_MAPPING = {
        "VUAA.L": "VUAA.UK",
        "CNDX.L": "CNDX.UK",
        "IGLN.L": "IGLN.UK",
        "IUIT.L": "IUIT.UK",
        "SPYL.DE": "SPYL.DE",
        "USDPLN=X": 'USDPLN',
        "EURPLN=X": "EURPLN"
    }

    ETF_CURRENCY = {
        "VUAA.UK": "USD",
        "CNDX.UK": "USD",
        "IGLN.UK": "USD",
        "IUIT.UK": "USD",
        "SPYL.DE": "EUR",
    }

    currency_groups = group_tickers_by_currency(tickers, ETF_CURRENCY)

    tickers_to_download = get_tickers_to_download(tickers, TICKER_MAPPING, ETF_CURRENCY)

    positions = Position.objects.filter(
        account_type=account_type,
        instrument_type__in=instrument_types
    )
    df_positions = pd.DataFrame({
        'symbol': [p.symbol for p in positions],
        'volume': [p.volume for p in positions],
        'open_time': [p.open_time for p in positions],
        'open_price': [p.open_price for p in positions]
        # p.open_time.date() can be use instead of df_sym.index.tz_localize
    })

    # start_date = positions.earliest('open_time').open_time.date()
    start_date = '2025-10-22'

    df_prices = yf.download(tickers_to_download, interval=period, start=start_date, auto_adjust=True)['Close']
    if period == '1h' or period == '30m':  # hourly data from yfinance is localized to UTC, daily is not localized
        # Convert to UTC+2
        df_prices.index = df_prices.index.tz_convert('Europe/Warsaw').tz_localize(None)

    df_prices.rename(columns=TICKER_MAPPING, inplace=True)
    df_prices = df_prices.ffill().bfill()

    df_cumvol = get_cumulative_volume(df_positions, tickers, period, df_prices.index)
    input_value_over_time = get_cumulative_input_value(df_positions, tickers, period, df_prices, currency_groups)
    logger.critical(input_value_over_time)
    df_price_pln = convert_prices_to_pln(df_prices, currency_groups)
    instruments_value = df_cumvol[tickers] * df_price_pln[tickers]

    portfolio_value = instruments_value.sum(axis=1)

    free_funds = free_funds_over_time(account_type, period)
    free_funds = free_funds.reindex(portfolio_value.index, method='ffill').fillna(0)
    total_portfolio_value = portfolio_value + free_funds

    logger.info(f'\n{portfolio_value}')
    logger.info(f'\n{free_funds}')
    logger.info(f'\n{total_portfolio_value}')

    df_to_save = pd.DataFrame({
        'input_value_over_time': input_value_over_time,
        'portfolio_value': portfolio_value,
        'free_funds': free_funds,
        'total_portfolio_value': total_portfolio_value
    })

    df_to_save.to_csv('../artifacts/portfolio_snapshots/portfolio_over_time.csv')

    # daily_change = portfolio_value.pct_change()


def get_tickers_to_download(tickers, ticker_mapping, etf_currency_mapping):
    tickers_to_download = [key for (key, value) in ticker_mapping.items() if value in tickers]
    fx_needed = {f"{cur}PLN=X" for cur in set(etf_currency_mapping[t] for t in tickers) if cur != "PLN"}
    tickers_to_download += list(fx_needed)
    return tickers_to_download


def group_tickers_by_currency(tickers, etf_currency_mapping):
    currency_groups = defaultdict(list)
    # Create a reverse mapping: { 'USD': [list of USD tickers], 'EUR': [list of EUR tickers], ... }
    for ticker in tickers:
        currency = etf_currency_mapping.get(ticker, "USD")  # default to USD if missing
        currency_groups[currency].append(ticker)
    return currency_groups


def convert_prices_to_pln(df_prices, currency_groups):
    df_price_pln = pd.DataFrame(index=df_prices.index)

    for currency, tickers_in_currency in currency_groups.items():
        if currency == "PLN":
            df_price_pln[tickers_in_currency] = df_prices[tickers_in_currency]
        else:
            fx_pair = f"{currency}PLN"  # e.g. "USDPLN", "EURPLN"
            if fx_pair not in df_prices.columns:
                raise ValueError(f"Missing FX rate column for {fx_pair}")
            df_price_pln[tickers_in_currency] = df_prices[tickers_in_currency].mul(df_prices[fx_pair], axis=0)

    return df_price_pln

def get_cumulative_input_value(df_positions, tickers, period, df_prices, currency_groups):
    df_input_value = pd.DataFrame(index=df_prices.index)

    for ticker in tickers:
        df_positions['open_time'] = standardize_datetime_by_period(df_positions['open_time'], period)

        df_ticker = df_positions[df_positions['symbol'] == ticker].copy()

        df_ticker['usd_value'] = df_ticker['open_price'] * df_ticker['volume']

        df_ticker = df_ticker[['open_time', 'usd_value']].set_index('open_time')

        df_ticker = df_ticker.merge(df_prices[['USDPLN', 'EURPLN']], left_index=True, right_index=True, how='left')

        # Determine base currency
        base_currency = None
        for currency, symbols in currency_groups.items():
            if ticker in symbols:
                base_currency = currency
                break
        if base_currency is None:
            raise ValueError(f"Ticker {ticker} not found in currency_groups")

        df_ticker['pln_value'] = df_ticker['usd_value'] * df_ticker[f'{base_currency}PLN']

        df_ticker = df_ticker.groupby('open_time', as_index=True)['pln_value'].sum()

        df_input_value[ticker] = df_ticker

    df_input_value = df_input_value.fillna(0)

    df_input_value['total_pln'] = df_input_value.sum(axis=1)
    df_input_value['total_pln_cumulative'] = df_input_value['total_pln'].cumsum()
    # df_input_value.to_csv('../artifacts/portfolio_snapshots/df_input_value.csv')
    # df_input_value_cumulative = df_input_value.sum(axis=0)
    return df_input_value['total_pln_cumulative']


def get_cumulative_volume(df_positions, tickers, period, index):
    df_cumvol = pd.DataFrame(index=index)

    for ticker in tickers:
        df_positions['open_time'] = standardize_datetime_by_period(df_positions['open_time'], period)

        df_sym = (
            df_positions[df_positions['symbol'] == ticker]
            .groupby('open_time')['volume']
            .sum()
            .sort_index()  # .reset_index()
        )

        cum_vol = (
            df_sym  # .set_index('open_time')['volume']
            .cumsum()
            .reindex(index, method='ffill')
            .fillna(0)
        )
        df_cumvol[ticker] = cum_vol

    return df_cumvol


def free_funds_over_time(account_type, period):
    cash_ops = CashOperation.objects.filter(account_type=account_type)

    df_cash_ops = pd.DataFrame({
        'time': [d.time for d in cash_ops],
        'amount': [d.amount for d in cash_ops]
    })

    df_cash_ops['time'] = standardize_datetime_by_period(df_cash_ops['time'], period)

    df_cumulative_cash = (
        df_cash_ops.groupby('time')['amount']
        .sum()
        .cumsum()
    )

    return df_cumulative_cash


def standardize_datetime_by_period(
        data: pd.Series | pd.DataFrame | pd.Index,
        period: str
) -> pd.Series | pd.DataFrame | pd.Index:
    """
    Standardize datetime values or index by period.

    - Removes timezone information.
    - If period == '1d', normalizes to midnight (00:00:00).
    - If period == '1h', keeps hour/minute but removes tz.

    For DataFrames, a copy is made before modifying the index to avoid
    mutating the caller's original object. Series and Index inputs don't
    need copying, since a new object or immutable index is returned anyway.

    Parameters
    ----------
    data : pd.Series | pd.DataFrame | pd.Index
        Object containing datetimes (either as values or index).
    period : str
        Period string ('1d' or '1h').

    Returns
    -------
    pd.Series | pd.DataFrame | pd.Index
        Object with standardized datetimes.
    """

    # Define transformation function
    def _standardize(dt_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
        dt_index = dt_index.tz_localize(None)
        if period == "1d":
            return dt_index.normalize()
        elif period == "1h":
            return dt_index
        else:
            raise ValueError(f"Invalid period: {period}")

    # Handle DatetimeIndex
    if isinstance(data, pd.DatetimeIndex):
        return _standardize(data)

    # Handle Series of datetimes
    elif isinstance(data, pd.Series) and pd.api.types.is_datetime64_any_dtype(data):
        dt_index = pd.DatetimeIndex(data)
        standardized_index = _standardize(dt_index)
        return pd.Series(standardized_index, index=data.index, name=data.name)

    # Handle DataFrame with datetime index
    elif isinstance(data, pd.DataFrame) and isinstance(data.index, pd.DatetimeIndex):
        data = data.copy()
        data.index = _standardize(data.index)
        return data

    else:
        raise TypeError(
            "Input must be a pandas Series, DataFrame with DatetimeIndex, or DatetimeIndex."
        )


class PortfolioDetails:
    def __init__(self):
        # Base querysets
        self.open_positions = Position.objects.filter(status="open")
        self.closed_positions = Position.objects.filter(status="close")
        self.cash_operations = CashOperation.objects.all()

    # Entry point for chaining
    def get_ops(self, type='positions'):
        if type == 'positions':
            return PortfolioQS(self.open_positions, self.closed_positions)
        elif type == 'open_pos':
            return PortfolioQS(self.open_positions)
        elif type == 'closed_pos':
            return PortfolioQS(self.closed_positions)
        elif type == 'cash_ops':
            return PortfolioQS(self.cash_operations)
        else:
            raise ValueError(f"Unknown type {type}")


class PortfolioQS:
    """
    Wraps a queryset (or multiple querysets) and provides chainable methods.
    """

    def __init__(self, *querysets):
        self.qs_list = list(querysets)
        # Start with first queryset by default for operations
        self.qs = self.qs_list[0] if self.qs_list else None

    # ------------------------
    # Filters
    # ------------------------
    def get_acc_pos(self, account_type):
        if self.qs is not None:
            self.qs = self.qs.filter(account_type=account_type)
        return self

    def get_instrument_pos(self, instrument):
        if self.qs is not None:
            self.qs = self.qs.filter(symbol=instrument)
        return self

    def get_cfd(self):
        if self.qs is not None:
            self.qs = self.qs.filter(instrument_type="CFD")
        return self

    def get_non_cfd(self):
        if self.qs is not None:
            self.qs = self.qs.exclude(instrument_type="CFD")
        return self

    def get_interest(self):
        if self.qs is not None:
            self.qs = self.qs.filter(type="Free-funds Interest")
        return self

    def get_interest_tax(self):
        if self.qs is not None:
            self.qs = self.qs.filter(type="Free-funds Interest Tax")
        return self

    def get_deposit(self):
        if self.qs is not None:
            self.qs = self.qs.filter(type__in=["deposit", "IKE Deposit", "IKZE Deposit"])
        return self

    # ------------------------
    # Aggregations / Computations
    # ------------------------
    # def free_funds(self):
    #     if self.qs is None:
    #         return 0
    #     return self.compute_purchase_value() + self.compute_profit() or 0

    # def uninvested_deposit(self):
    #     if self.qs is None:
    #         return 0
    #     return self.agg_deposit() - self.compute_purchase_value() or 0

    def agg_deposit(self):
        if self.qs is None:
            return 0
        return self.qs.aggregate(total=Sum("amount"))["total"] or 0

    def compute_purchase_value(self):
        if self.qs is None:
            return 0
        return self.qs.aggregate(total=Sum("purchase_value"))["total"] or 0

    def compute_profit(self):
        if self.qs is None:
            return 0
        return self.qs.aggregate(total=Sum("gross_pl"))["total"] or 0

    def compute_current_value(self):
        if self.qs is None:
            return 0
        return self.compute_purchase_value() + self.compute_profit() or 0

    def compute_cfd_gain(self):
        if self.qs is None:
            return 0
        agg = self.qs.aggregate(gross=Sum("gross_pl"), swap=Sum("swap"))
        return (agg["gross"] or 0) + (agg["swap"] or 0)

    def compute_non_cfd_gain(self):
        if self.qs is None:
            return 0
        agg = self.qs.aggregate(gross=Sum("gross_pl"), swap=Sum("swap"))
        return (agg["gross"] or 0) + (agg["swap"] or 0)
