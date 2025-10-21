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
    get_positions_value_over_time('ikze', instrument_types, ['VUAA.UK'])

    # Step 4: Fetch the widget instance
    widget = get_object_or_404(Widget, id='28c2eaf5-ddde-4981-b88e-238cd6ef5419')

    # Step 5: Assign widget_data (dict) to the data field
    widget.data = widget_data

    # Step 6 :Save it
    widget.save()
    logger.debug(f"Updated widget {widget.id} with new data ({len(widget_data)} items).")


def get_positions_value_over_time(account_type, instrument_types, tickers):
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

    tickers_to_download = [key for (key, value) in TICKER_MAPPING.items() if value in tickers]

    currency_groups = defaultdict(list)
    # Create a reverse mapping: { 'USD': [list of USD tickers], 'EUR': [list of EUR tickers], ... }
    for ticker in tickers:
        currency = ETF_CURRENCY.get(ticker, "USD")  # default to USD if missing
        currency_groups[currency].append(ticker)

    fx_needed = {f"{cur}PLN=X" for cur in set(ETF_CURRENCY[t] for t in tickers) if cur != "PLN"}
    tickers_to_download += list(fx_needed)

    positions = Position.objects.filter(
        account_type=account_type,
        instrument_type__in=instrument_types
    )

    start_date = positions.earliest('open_time').open_time.date()

    df_prices = yf.download(tickers_to_download, interval="1d", start=start_date)['Close']
    # df_prices.index = df_prices.index.tz_convert("Europe/Warsaw").tz_localize(None)
    df_prices.rename(columns=TICKER_MAPPING, inplace=True)
    df_prices.ffill(inplace=True)

    df_positions = pd.DataFrame({
        'symbol': [p.symbol for p in positions],
        "volume": [p.volume for p in positions],
        "open_time": [p.open_time.date() for p in positions]
    })

    df_cumvol = pd.DataFrame(index=df_prices.index)
    for ticker in tickers:
        df_sym = (
            df_positions[df_positions['symbol'] == ticker]
            .groupby('open_time')['volume']
            .sum()
            .sort_index()
            .reset_index()
        )
        cum_vol = (
            df_sym.set_index('open_time')['volume']
            .cumsum()
            .reindex(df_prices.index, method='ffill')
            .fillna(0)
        )
        df_cumvol[ticker] = cum_vol

    # Prepare price dataframe
    df_price_pln = pd.DataFrame(index=df_prices.index)


    for currency, tickers_in_currency in currency_groups.items():
        if currency == "PLN":
            df_price_pln[tickers_in_currency] = df_prices[tickers_in_currency]
        else:
            fx_pair = f"{currency}PLN"  # e.g. "USDPLN", "EURPLN"
            if fx_pair not in df_prices.columns:
                raise ValueError(f"Missing FX rate column for {fx_pair}")
            df_price_pln[tickers_in_currency] = df_prices[tickers_in_currency].mul(df_prices[fx_pair], axis=0)



    instruments_value = df_cumvol[tickers] * df_price_pln[tickers]
    portfolio_value = instruments_value.sum(axis=1)
    # logger.info(f'\n{portfolio_value}')

    total_portfolio_value = free_funds_over_time(portfolio_value)
    # logger.info(total_portfolio_value)

    # daily_change = portfolio_value.pct_change()


def free_funds_over_time(portfolio_value):
    deposits = CashOperation.objects.filter(account_type='ikze')
    # logger.info(deposits.aggregate(total=Sum("amount"))["total"])
    df_deposits = pd.DataFrame({
        'time': [d.time for d in deposits],
        'amount': [d.amount for d in deposits]
    })

    # DO THIS IF DAILY, NOT HOURLY
    # df_deposits['time'] = df_deposits['time'].dt.normalize()

    df_cumulative_cash = (
        df_deposits.groupby('time')['amount']
        .sum()
        .cumsum()
    )

    # df_cumulative_cash.index = df_cumulative_cash.index.tz_convert("Europe/Warsaw").tz_localize(None)  # this is already Poland time, even though its UTC+0
    df_cumulative_cash.index = df_cumulative_cash.index.tz_localize(None)  # this is already Poland time, even though its UTC+0

    df_cumulative_cash = df_cumulative_cash.reindex(portfolio_value.index, method='ffill').fillna(0)

    # add cumulative cash deposits (uninvested cash)
    total_portfolio_value = portfolio_value + df_cumulative_cash
    # logger.error(df_cumulative_cash)

    return total_portfolio_value

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
