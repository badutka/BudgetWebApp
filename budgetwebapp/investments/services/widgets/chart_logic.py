from datetime import datetime
import pandas as pd
from pathlib import Path

from django.db.models import Sum

from investments.models import Position, Instrument, CashOperation, OverviewWidget
from investments.services.valuation.datetime_utils import standardize_datetime_by_period
from investments.services.valuation import metrics
from core.datastore import DataStore
from core.logger import logger
from core.constants import MARKET_DATA_PATH

from .registry import register_widget


class BaseWidgetLogic:
    def __init__(self, widget):
        self.widget = widget

    def update_data(self):
        raise NotImplementedError


class VariantWidgetLogic(BaseWidgetLogic):

    def update_data(self):
        widget = self.widget.get_real_instance()
        variant = getattr(widget, "variant", None) or widget.config.get("variant", "default")
        handler = getattr(self, f"variant_{variant}", None)
        if not handler:
            raise NotImplementedError(
                f"No handler defined for variant '{variant}' in {self.__class__.__name__}"
            )
        handler()

    def variant_default(self):
        raise NotImplementedError


@register_widget("chart", 'timeseries')
class TimeSeriesChartLogic(VariantWidgetLogic):
    def variant_default(self):
        self.widget.data = {
            'date': ['2025-10-11', '2025-10-17'],
            'invested_value': [1, 2],
            'portfolio_value': [6, 7]
        }

    def variant_ike_account_over_time(self):
        file_name = "account_data_ike"
        df_account_over_time = DataStore(Path(MARKET_DATA_PATH)).load(file_name, fmt='csv', prefix='').to_dict(orient='list')

        self.widget.data = {
            'date': df_account_over_time['date'][::12],
            'invested_value': df_account_over_time['invested_value'][::12],
            'portfolio_value': df_account_over_time['portfolio_value'][::12]
        }

    def variant_main_account_over_time(self):
        file_name = "account_data_main"
        df_account_over_time = DataStore(Path(MARKET_DATA_PATH)).load(file_name, fmt='csv', prefix='').to_dict(orient='list')
        # df_account_over_time1 = DataStore(Path(MARKET_DATA_PATH)).load(file_name, fmt='csv', prefix='').set_index('date')
        # df_account_over_time2 = DataStore(Path(MARKET_DATA_PATH)).load("account_data_ike", fmt='csv', prefix='').set_index('date')
        # df_account_over_time3 = DataStore(Path(MARKET_DATA_PATH)).load("account_data_ikze", fmt='csv', prefix='').set_index('date')
        # df_account_over_time = df_account_over_time1 + df_account_over_time2 + df_account_over_time3
        # print(df_account_over_time)
        # df_account_over_time = df_account_over_time.reset_index().to_dict(orient='list')

        self.widget.data = {
            'date': df_account_over_time['date'][::12],
            'invested_value': df_account_over_time['invested_value'][::12],
            'portfolio_value': df_account_over_time['portfolio_value'][::12]
        }


@register_widget("chart", 'pie')
class PieChartLogic(VariantWidgetLogic):
    def variant_default(self):
        self.widget.data = {
            'labels': ['variant_default'],
            'values': [111]
        }

    def variant_ike_account_allocation(self):
        self.widget.data = {
            'labels': ['label1', 'label2', 'label3'],
            'values': [50, 100, 150]
        }

    def variant_currency_allocation(self):
        self.widget.data = {
            'labels': ['variant_currency_allocation'],
            'values': [333]
        }


@register_widget('overview')
class OverviewLogic(BaseWidgetLogic):
    def update_data(self):
        # self.data = {} if not self.data else self.data
        widget_data = {}
        adj = 0.995

        self.account_type = self.widget.config.get("account_type", "main")  # type: ignore
        self.instrument_types = self.widget.config.get("labels", {}).get("instrument_types", None)  # type: ignore
        self.limit = self.widget.config.get("limit", 0)  # type: ignore

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

        df_fx_melted = df_fx_rates.reset_index().rename(columns={'Date': 'date'}).melt(id_vars='date',
                                                                                       var_name='fx_symbol',
                                                                                       value_name='open_fx_rate')
        result = result.merge(df_fx_melted, how='left', on=['date', 'fx_symbol'])

        # gross_pl percentages require conversion to PLN, to include USDPLN volatility, but it might be useful
        # to look at the performance of instrument in its base currency alone, todo
        # result["current_price"] = result["symbol"].map(current_prices)
        result["current_price_total"] = result["symbol"].map(current_prices) * result["volume"]
        result["current_price_total_pln"] = result["current_price_total"] * result[
            'current_fx_rate'] * adj  # total_value
        result["open_price_total_pln"] = result["open_price_total"] * result["open_fx_rate"] * (
                1 / adj)  # invested_value
        result['gross_pl_pln'] = result["current_price_total_pln"] - result["open_price_total_pln"]  # profit
        result['holding_years'] = (datetime.now() - result['date']).dt.total_seconds() / (365.25 * 24 * 3600)

        # Use df_prices index as the reference for full time grid
        full_index = df_prices.index.rename('date')  # hourly timestamps

        # Reindex required data
        # pivot_table with aggfunc ensures aggregation is explicit and reduces risk if duplicates exist
        df_volumes_tickers = result.pivot_table(index='date', columns='symbol', values='volume_cumulative',
                                                aggfunc='last')
        df_volumes_tickers = df_volumes_tickers.reindex(full_index).ffill().fillna(0)
        df_prices_tickers = df_prices[df_volumes_tickers.columns]
        df_prices_tickers = df_prices_tickers.reindex(full_index).ffill()
        df_fx_rates = df_fx_rates.reindex(full_index).ffill()

        df_fx_rates_tickers = pd.DataFrame(
            {s: df_fx_rates[currency_to_fx.get(curr)] if currency_to_fx.get(curr) else 1.0
             for s, curr in currency_map.items()}, index=full_index)

        portfolio_value = pd.DataFrame()
        portfolio_value['invested_value'] = (
            result.groupby("date")["open_price_total_pln"].sum().reindex(full_index).fillna(0).cumsum())  # * (1 / adj)
        portfolio_value['portfolio_value'] = (df_volumes_tickers * df_prices_tickers * df_fx_rates_tickers).sum(
            axis=1) * adj
        portfolio_value['free_funds'] = self._get_cash_cumulative_df(self.account_type, '1h').reindex(
            portfolio_value.index, method='ffill').fillna(0)
        portfolio_value['total_portfolio_value'] = portfolio_value['portfolio_value'] + portfolio_value['free_funds']
        portfolio_value['total_portfolio_value'] = portfolio_value['total_portfolio_value']  # * 0.995
        self._save_account_data(portfolio_value, self.account_type)

        profit = result['gross_pl_pln'].sum()
        invested_value = result['open_price_total_pln'].sum()
        current_value = result['current_price_total_pln'].sum()
        free_funds = self._get_latest_values(portfolio_value['free_funds'])
        total_value = current_value + free_funds

        # CAGR and CAGR
        cagr = metrics.Metric.new_cagr_v3(invested_value, current_value, result['date'].iloc[0])
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

        widget_data['total_value'] = total_value
        widget_data['profit'] = profit
        widget_data['free_funds'] = free_funds
        widget_data['instruments_info'] = instruments_info
        widget_data['metrics'] = {'cagr': cagr, 'wcagr': wcagr, 'twr': twr}
        widget_data['metrics_changes'] = periodic_metrics

        if self.limit > 0:
            progress_current, progress_current_pct = self._get_progress_amount(self.account_type, self.limit)
            widget_data['progress_current'] = progress_current
            widget_data['progress_current_pct'] = progress_current_pct

        self.widget.data = widget_data

    def update_allocation(self):
        """
        Fetches all OverviewWidget instances from the database,
        calculates the total portfolio value, and updates this widget's
        'allocation_perc' field inside self.data.
        """
        self.widget.data = self.widget.data or {}  # Ensure the widget's data exists

        all_widgets = OverviewWidget.objects.filter(widget_type='overview')

        total_all = 0.0
        for w in all_widgets:
            data = getattr(w, "data", {}) or {}
            total_all += data.get("total_value", 0.0)

        current_value = self.widget.data.get("total_value", 0.0)
        allocation_perc = current_value / total_all if total_all > 0 else 0.0

        self.widget.data["allocation_perc"] = allocation_perc

        return allocation_perc

    def _save_account_data(self, data_df, account_type):
        file_name = f"account_data_{account_type}"
        DataStore(Path(MARKET_DATA_PATH)).save(file_name, data_df.reset_index(), fmt='csv', prefix='')

    def _get_prices_df(self):
        file_name = "market_prices_1h"
        df_prices = DataStore(Path(MARKET_DATA_PATH)).load(file_name, fmt='parquet', prefix='')
        return df_prices

    def _get_latest_values(self, df_prices):
        if isinstance(df_prices, pd.DataFrame):
            return df_prices.iloc[-1].to_dict()  # to_frame().T.reset_index(drop=True)
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
