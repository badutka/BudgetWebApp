from pathlib import Path

import numpy as np
import pandas as pd
from datetime import datetime

from django.db import models
import uuid
from django.core.validators import MinLengthValidator
from django.db.models import Sum

from core.datastore import DataStore
from investments.services.valuation.datetime_utils import standardize_datetime_by_period
from investments.services.valuation import metrics
from core.logger import logger


class BaseModel(models.Model):
    """Abstract base class to satisfy Pycharm type checking."""
    objects = models.Manager()

    class Meta:
        abstract = True


class Dashboard(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Widget(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey('Dashboard', on_delete=models.CASCADE, related_name='widgets')
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=50, blank=True, null=True)  # optional reference

    # Grid position
    row = models.PositiveIntegerField(default=1)
    column = models.PositiveIntegerField(default=1)
    width_units = models.PositiveIntegerField(default=1)
    height_units = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.title


class BaseWidget(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey('Dashboard', on_delete=models.CASCADE, related_name='base_widgets')
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=50, blank=True, null=True)  # optional reference

    # Grid position
    row = models.PositiveIntegerField(default=1)
    column = models.PositiveIntegerField(default=1)
    width_units = models.PositiveIntegerField(default=1)
    height_units = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    data = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title


class OverviewWidget(BaseWidget):
    widget_type = 'overview'

    def update_widget_data(self):
        self.data = {} if not self.data else self.data
        widget_data = {}
        adj = 0.995

        self.account_type = self.config.get("account_type", "main")  # type: ignore
        self.instrument_types = self.config.get("labels", {}).get("instrument_types", None)  # type: ignore
        self.limit = self.config.get("limit", 0)  # type: ignore

        positions = Position.objects.filter(account_type=self.account_type, status="open")
        positions_df = self._get_positions_df(positions)

        tickers = list(positions.values_list('symbol', flat=True).order_by('symbol').distinct())
        self.instruments = Instrument.objects.filter(symbol__in=tickers)

        instruments_info = {i.symbol: {'logo_url': i.logo_url} for i in self.instruments}
        currency_map = {i.symbol: i.currency for i in self.instruments}

        # currencies = list(set(self.instruments.values_list('currency', flat=True)))

        df_prices = self._get_prices_df()

        positions_df['open_time'] = standardize_datetime_by_period(positions_df['open_time'], '1h')
        positions_df['open_time'] = positions_df['open_time'].dt.ceil('h')
        positions_df = positions_df.set_index('open_time').sort_index()
        positions_df = positions_df.reset_index().rename(columns={"open_time": "date"})
        positions_df["open_price_total"] = positions_df["open_price"] * positions_df["volume"]

        # Setup cumulation of volume in the next groupby
        positions_df["volume_cumsum"] = positions_df.sort_index().groupby("symbol")["volume"].cumsum()

        result = (positions_df.groupby(['date', 'symbol']).agg(
            open_price_total=('open_price_total', 'sum'),
            volume=('volume', 'sum'),
            volume_cumulative=('volume_cumsum', 'last')
        )).reset_index()

        current_prices = self._get_latest_values(df_prices)

        result["currency"] = result["symbol"].map(currency_map)
        result["fx_symbol"] = result["currency"] + "PLN"
        result['current_fx_rate'] = result["fx_symbol"].map(current_prices).fillna(1.0)

        fx_cols = df_prices.filter(like='PLN').columns.tolist()
        df_fx_rates = df_prices[fx_cols].copy()

        # Build a dynamic currency -> FX mapping from column names
        currency_to_fx = {fx[:-3]: fx for fx in fx_cols}  # 'USD' -> 'USDPLN', 'EUR' -> 'EURPLN'
        currency_to_fx["PLN"] = None  # means "no conversion needed"

        df_fx_melted = df_fx_rates.reset_index().rename(columns={'Date': 'date'}).melt(id_vars='date', var_name='fx_symbol', value_name='open_fx_rate')
        result = result.merge(df_fx_melted, how='left', on=['date', 'fx_symbol'])

        # gross_pl percentages require conversion to PLN, to include USDPLN volatility, but it might be useful
        # to look at the performance of instrument in its base currency alone, todo
        # result["current_price"] = result["symbol"].map(current_prices)
        result["current_price_total"] = result["symbol"].map(current_prices) * result["volume"]
        result["current_price_total_pln"] = result["current_price_total"] * result['current_fx_rate'] * adj  # total_value
        result["open_price_total_pln"] = result["open_price_total"] * result["open_fx_rate"] * (1 / adj)  # invested_value
        result['gross_pl_pln'] =  result["current_price_total_pln"] - result["open_price_total_pln"]  # profit
        result['holding_years'] = (datetime.now() - result['date']).dt.total_seconds() / (365.25 * 24 * 3600)

        # Use df_prices index as the reference for full time grid
        full_index = df_prices.index.rename('date')  # hourly timestamps

        # Reindex required data
        # pivot_table with aggfunc ensures aggregation is explicit and reduces risk if duplicates exist
        df_volumes_tickers = result.pivot_table(index='date', columns='symbol', values='volume_cumulative', aggfunc='last')
        df_volumes_tickers = df_volumes_tickers.reindex(full_index).ffill().fillna(0)
        df_prices_tickers = df_prices[df_volumes_tickers.columns]
        df_prices_tickers = df_prices_tickers.reindex(full_index).ffill()
        df_fx_rates = df_fx_rates.reindex(full_index).ffill()

        df_fx_rates_tickers = pd.DataFrame({s: df_fx_rates[currency_to_fx.get(curr)] if currency_to_fx.get(curr) else 1.0
                              for s, curr in currency_map.items()}, index=full_index)

        portfolio_value = pd.DataFrame()
        portfolio_value['invested_value'] = (result.groupby("date")["open_price_total_pln"].sum().reindex(full_index).fillna(0).cumsum())# * (1 / adj)
        portfolio_value['portfolio_value'] = (df_volumes_tickers * df_prices_tickers * df_fx_rates_tickers).sum(axis=1) * adj
        portfolio_value['free_funds'] = self._get_cash_cumulative_df(self.account_type, '1h').reindex(portfolio_value.index, method='ffill').fillna(0)
        portfolio_value['total_portfolio_value'] = portfolio_value['portfolio_value'] + portfolio_value['free_funds']
        portfolio_value['total_portfolio_value'] = portfolio_value['total_portfolio_value']# * 0.995

        profit = result['gross_pl_pln'].sum()
        invested_value = result['open_price_total_pln'].sum()
        total_value = result['current_price_total_pln'].sum()

        # CAGR and CAGR
        cagr = metrics.Metric.new_cagr_v3(invested_value, total_value, result['date'].iloc[0])
        wcagr = metrics.Metric.new_weighted_cagr_v2(result["open_price_total_pln"], result["current_price_total_pln"],
                                                    result['holding_years'])

        # Global TWR
        twr_data = portfolio_value[['invested_value', 'portfolio_value']]
        twr = metrics.Metric.twr_v2(twr_data, time_period='total')

        # Periodic TWR
        periodic_metrics = {
            'D': metrics.Metric.twr_v2(twr_data, time_period='today'),
            'W': metrics.Metric.twr_v2(twr_data, time_period='last_week'),
            'M': metrics.Metric.twr_v2(twr_data, time_period='last_month'),
        }

        # Global HPR per ticker
        hpr_data = pd.DataFrame({
            'start': result.groupby(['symbol'])["open_price_total_pln"].sum(),  # * (1 / 0.995),
            'end': result.groupby(['symbol'])["current_price_total_pln"].sum()
        })
        hpr = hpr_data['end'] / hpr_data['start'] - 1

        for ticker, info in instruments_info.items():
            info['hpr'] = float(hpr[ticker])

        widget_data['total_value'] = result['current_price_total_pln'].sum()
        widget_data['profit'] = profit
        widget_data['free_funds'] = self._get_latest_values(portfolio_value['free_funds'])
        widget_data['instruments_info'] = instruments_info
        widget_data['metrics'] = {'cagr': cagr, 'wcagr': wcagr, 'twr': twr}
        widget_data['metrics_changes'] = periodic_metrics

        if self.limit > 0:
            progress_current, progress_current_pct = self._get_progress_amount(self.account_type, self.limit)
            widget_data['progress_current'] = progress_current
            widget_data['progress_current_pct'] = progress_current_pct

        self.data = widget_data


    def _get_prices_df(self):
        file_path = Path(__file__).parent.parent.parent / "artifacts/market_data"
        file_name = "market_prices_1h"
        df_prices = DataStore(file_path).load(file_name, fmt='parquet', prefix='')
        return df_prices

    def _get_latest_values(self, df_prices):
        if isinstance(df_prices, pd.DataFrame):
            return df_prices.iloc[-1].to_dict()#to_frame().T.reset_index(drop=True)
        return df_prices.iloc[-1]

    def _get_positions_df(self, positions):
        df_positions = pd.DataFrame(list(positions.values('open_time', 'symbol', 'open_price', 'volume')))
        return df_positions

    def _get_cash_cumulative_df(self, account_type, period):
        cash_ops = CashOperation.objects.filter(account_type=account_type)
        df_cash_ops = pd.DataFrame(cash_ops.values('time', 'amount'))
        df_cash_ops['time'] = standardize_datetime_by_period(df_cash_ops['time'], period)
        cash_cumulative_df = (
            df_cash_ops.groupby('time')['amount']
            .sum()
            .cumsum()
        )
        return cash_cumulative_df

    def _get_progress_amount(self, account_type, limit):
        progress_current = (
                CashOperation.objects.filter(account_type=account_type, type=f"{account_type.upper()} Deposit")
                .aggregate(total=Sum('amount'))['total'] or 0
        )
        progress_current_pct = progress_current / limit
        return progress_current, progress_current_pct

    # def save(self, *args, **kwargs):
    #     # compute/update before saving
    #     self.update_widget_data()
    #     super().save(*args, **kwargs)


class Position(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    symbol = models.CharField(max_length=50)
    status = models.CharField(max_length=10)  # 'open' or 'closed'
    account_type = models.CharField(max_length=10)  # 'main', 'ike', 'ikze'

    open_time = models.DateTimeField()
    close_price = models.FloatField(null=True, blank=True)
    open_price = models.FloatField(null=True, blank=True)
    market_price = models.FloatField(null=True, blank=True)

    volume = models.FloatField()
    purchase_value = models.FloatField()
    gross_pl = models.FloatField(verbose_name="Gross P/L")
    gross_pl_perc = models.FloatField(null=True, blank=True)
    swap = models.FloatField(default=0.0)

    direction = models.CharField(max_length=100, null=True, blank=True)
    position_id = models.CharField(max_length=100, null=True, blank=True)
    instrument_type = models.CharField(max_length=20, null=True, blank=True)  # 'CFD', 'ETF', etc.

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["symbol", "account_type", "status"]),
        ]
        verbose_name_plural = "Positions"
        ordering = ["-open_time"]

    def __str__(self):
        return f"{self.id} ({self.symbol}) {self.open_time}, {self.purchase_value})"


class Instrument(BaseModel):
    CFD = 'CFD'
    ETF = 'ETF'
    ETC = 'ETC'
    STOCK = 'STOCK'

    INSTRUMENT_TYPES = [
        (CFD, 'CFD'),
        (ETF, 'ETF'),
        (ETC, 'ETC'),
        (STOCK, 'Stock'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    symbol = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    isin = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        unique=True,
        help_text="International Securities Identification Number (ISIN)"
    )
    instrument_type = models.CharField(
        max_length=20,
        choices=INSTRUMENT_TYPES,
        blank=True,
        null=True,
    )
    currency = models.CharField(
        max_length=3,
        validators=[MinLengthValidator(3)],
        blank=True,
        null=True,
        help_text="Currency of the instrument (e.g. USD, EUR)"
    )

    logo_url = models.URLField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.logo_url and self.symbol:
            formatted_symbol = self.symbol.lower().replace('.', '_')
            self.logo_url = f"https://logos.xtb.com/{formatted_symbol}.svg"

        if self.currency:
            self.currency = self.currency.upper()

        super().save(*args, **kwargs)

    def __str__(self):
        display_name = self.name or self.symbol
        return f"{display_name} ({self.instrument_type or 'Unknown'})"


class CashOperation(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xtb_id = models.CharField(max_length=50, unique=True)

    time = models.DateTimeField()
    symbol = models.CharField(max_length=50, null=True, blank=True)
    type = models.CharField(max_length=100)
    amount = models.FloatField()
    account_type = models.CharField(max_length=10)  # 'main', 'ike', 'ikze'

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["account_type", "time"]),
        ]
        verbose_name_plural = "CashOperations"
        ordering = ["-time"]

    def __str__(self):
        return f"{self.id} ({self.xtb_id}) {self.time}, {self.symbol})"
