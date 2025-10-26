from pathlib import Path
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
        currencies = list(set(self.instruments.values_list('currency', flat=True)))

        df_prices = self._get_prices_df()
        df_prices_pln = self._convert_prices_to_pln(df_prices, currency_map) * adj
        df_prices_pln = df_prices_pln[tickers]
        self.latest_prices = self._get_latest_values(df_prices_pln)

        positions_df['open_time'] = standardize_datetime_by_period(positions_df['open_time'], '1h')
        positions_df['open_time'] = positions_df['open_time'].dt.ceil('h')
        positions_df = positions_df.set_index('open_time').sort_index()
        # todo: merge df_prices_pln instead; required hanlding open_price too
        positions_df = positions_df.merge(df_prices, left_index=True, right_index=True, how='left')

        invested_amount_df = pd.DataFrame(index=df_prices.index)
        volume_cumulative_df = pd.DataFrame(index=df_prices.index)
        df_positions_cagr = pd.DataFrame()
        c = 0
        # Performs grouping once (O(n)) instead of O(nt) scans.
        # positions_by_ticker = dict(tuple(positions_df.groupby("symbol")))
        # for ticker, df_positions_ticker in positions_by_ticker.items():
        # For many tickers, this could be slower than a vectorized approach using pivot_table or groupby + transform.
        # todo: explore possibility of groupby to replace the loop entirely
        for ticker, df_positions_ticker in positions_df.groupby("symbol"):
            currency = currency_map[ticker]
            df_positions_ticker = df_positions_ticker[['volume', 'open_price', 'symbol', f'{currency}PLN']].copy()

            df_positions_ticker['open_price_total'] = df_positions_ticker['open_price'] * df_positions_ticker['volume']
            df_positions_ticker['open_price_total_pln'] = df_positions_ticker['open_price_total'] * df_positions_ticker[f'{currency}PLN']
            # df_positions_ticker['gross_pl'] = self.latest_prices[ticker] * df_positions_ticker['volume'] * self.latest_prices[f'{currency}PLN'] * adj - df_positions_ticker['open_price_total_pln']
            df_positions_ticker['gross_pl'] = self.latest_prices[ticker] * df_positions_ticker['volume'] - df_positions_ticker['open_price_total_pln']
            df_positions_ticker['volume_cumulative'] = df_positions_ticker['volume'].cumsum()
            c = c + df_positions_ticker['gross_pl'].sum()
            invested_amount_df[ticker] = df_positions_ticker.groupby(df_positions_ticker.index)['open_price_total_pln'].sum()
            volume_cumulative_df[ticker] = df_positions_ticker.groupby(df_positions_ticker.index)['volume_cumulative'].last()

            df_positions_ticker['holding_years'] = (datetime.now() - df_positions_ticker.index).total_seconds() / (365.25 * 24 * 3600)
            df_positions_cagr = pd.concat([df_positions_cagr, df_positions_ticker[['open_price_total_pln', 'gross_pl', 'holding_years']]])

        invested_amount_df = self._transform_invested_amount_df(invested_amount_df)
        volume_cumulative_df = volume_cumulative_df.ffill().fillna(0)
        instruments_cumulative_value_pln = volume_cumulative_df.mul(df_prices_pln, axis=0)  # can use [tickers] slice to ensure proper order

        portfolio_value = instruments_cumulative_value_pln.sum(axis=1)
        tickers_total_value = self._get_latest_values(instruments_cumulative_value_pln)
        invested_total_amount = self._get_latest_values(invested_amount_df[tickers].cumsum())
        cash_cumulative_df = self._get_cash_cumulative_df(self.account_type, '1h').reindex(portfolio_value.index, method='ffill').fillna(0)

        # positions_df['volume_cumulative'] = positions_df.groupby('symbol')['volume'].cumsum()
        # print(positions_df)

        hpr = metrics.Metric.HPR(pd.DataFrame(invested_total_amount, index=[0]) * (1 / 0.995), pd.DataFrame(tickers_total_value, index=[0]))

        widget_data['total_value'] = self._get_latest_values(portfolio_value + cash_cumulative_df)
        # pd.Series(tickers_total_value.values()).fillna(0).sum()
        widget_data['profit'] = sum(tickers_total_value.values()) - sum(invested_total_amount.values())
        widget_data['free_funds'] = self._get_latest_values(cash_cumulative_df)

        for ticker in tickers:
            instruments_info[ticker]['hpr'] = float(hpr[ticker].iloc[0])

        widget_data['instruments_info'] = instruments_info
        widget_data['metrics'] = {'cagr': metrics.Metric.new_cagr_v2(invested_amount_df['total_pln_cumulative'], portfolio_value)}
        widget_data['metrics']['wcagr'] = metrics.Metric.new_weighted_cagr(df_positions_cagr)
        twr_data = pd.concat([pd.DataFrame({'input_value_cumsum': invested_amount_df['total_pln_cumulative'], 'portfolio_value': portfolio_value})], axis=1)
        widget_data['metrics']['twr'] = metrics.Metric.twr(twr_data, time_period='total')

        widget_data['metrics_changes'] = {
            'D': metrics.Metric.twr(twr_data, time_period='today'),
            'W': metrics.Metric.twr(twr_data, time_period='last_week'),
            'M': metrics.Metric.twr(twr_data, time_period='last_month'),
        }
        if self.limit > 0:
            print('hello')
            progress_current, progress_current_pct = self._get_progress_amount(self.account_type, self.limit)
            widget_data['progress_current'] = progress_current
            widget_data['progress_current_pct'] = progress_current_pct

        self.data = widget_data

    def _get_prices_df(self):
        file_path = Path("../artifacts/market_data")
        file_name = "market_prices_1h"
        df_prices = DataStore(file_path).load(file_name, fmt='parquet', prefix='')
        return df_prices

    def _convert_prices_to_pln(self, df_prices: pd.DataFrame, currency_map: dict):
        df_prices_pln = df_prices.copy()

        currencies = {cur for cur in currency_map.values() if cur != 'PLN'}

        for cur in currencies:
            fx_col = f"{cur}PLN"
            if fx_col not in df_prices.columns:
                raise KeyError(f"FX rate column '{fx_col}' not found in df_prices")
            tickers = [t for t, c in currency_map.items() if c == cur and t in df_prices.columns]
            if tickers:
                df_prices_pln[tickers] = df_prices[tickers].mul(df_prices[fx_col], axis=0)

        fx_columns = [f"{cur}PLN" for cur in currencies if f"{cur}PLN" in df_prices.columns]
        df_prices_pln = df_prices_pln.drop(columns=fx_columns)

        return df_prices_pln

    def _get_latest_values(self, df_prices):
        if isinstance(df_prices, pd.DataFrame):
            return df_prices.iloc[-1].to_dict()#to_frame().T.reset_index(drop=True)
        return df_prices.iloc[-1]

    def _get_positions_df(self, positions):
        df_positions = pd.DataFrame({
            'open_time': [p.open_time for p in positions],
            'symbol': [p.symbol for p in positions],
            'open_price': [p.open_price for p in positions],
            'volume': [p.volume for p in positions]
        })
        return df_positions

    def _transform_invested_amount_df(self, invested_amount_df):
        invested_amount_df = invested_amount_df.fillna(0)
        invested_amount_df['total_pln'] = invested_amount_df.sum(axis=1)
        invested_amount_df['total_pln_cumulative'] = invested_amount_df['total_pln'].cumsum()
        return invested_amount_df

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

    def save(self, *args, **kwargs):
        # compute/update before saving
        self.update_widget_data()
        super().save(*args, **kwargs)


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
