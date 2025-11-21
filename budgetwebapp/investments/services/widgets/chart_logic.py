from datetime import datetime
import pandas as pd
from pathlib import Path

from django.db.models import F, Sum

from investments.models import Position, Instrument, CashOperation, OverviewWidget
from investments.services.valuation.datetime_utils import standardize_datetime_by_period
from investments.services.valuation import metrics
from investments.services.valuation import portfolio_engine
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
        df_account_over_time = DataStore(Path(MARKET_DATA_PATH)).load(file_name, fmt='csv', prefix='').to_dict(
            orient='list')

        self.widget.data = {
            'date': df_account_over_time['date'][::12],
            'invested_value': df_account_over_time['invested_value'][::12],
            'portfolio_value': df_account_over_time['portfolio_value'][::12]
        }

    def variant_main_account_over_time(self):
        file_name = "account_data_main"
        df_account_over_time = DataStore(Path(MARKET_DATA_PATH)).load(file_name, fmt='csv', prefix='').to_dict(
            orient='list')

        self.widget.data = {
            'date': df_account_over_time['date'][::12],
            'invested_value': df_account_over_time['invested_value'][::12],
            'portfolio_value': df_account_over_time['portfolio_value'][::12]
        }

    def variant_xtb_combined_account_over_time(self):
        file_name = "account_data_xtb_combined"
        df_account_over_time = DataStore(Path(MARKET_DATA_PATH)).load(file_name, fmt='csv', prefix='').to_dict(
            orient='list')

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
        account_type = self.widget.config.get("account_type", "main")
        account_allocation = self._get_account_allocation(account_type)

        self.widget.data = {
            "labels": account_allocation.index.tolist(),
            "values": account_allocation.values.round(2).tolist()
        }

    def variant_main_account_allocation(self):
        account_type = self.widget.config.get("account_type", "main")
        account_allocation = self._get_account_allocation(account_type)

        self.widget.data = {
            "labels": account_allocation.index.tolist(),
            "values": account_allocation.values.round(2).tolist()
        }

    def variant_xtb_combined_account_allocation(self):
        account_type = self.widget.config.get("account_type", "main")
        account_allocation = self._get_account_allocation(account_type)

        self.widget.data = {
            "labels": account_allocation.index.tolist(),
            "values": account_allocation.values.round(2).tolist()
        }

    def _get_account_allocation(self, account_type):
        df_volumes_tickers = DataStore(Path(MARKET_DATA_PATH)).load(f'volumes_tickers_{account_type}', fmt='csv',
                                                                    prefix='')
        df_prices_tickers = DataStore(Path(MARKET_DATA_PATH)).load(f'prices_tickers_{account_type}', fmt='csv',
                                                                   prefix='')
        df_fx_rates_tickers = DataStore(Path(MARKET_DATA_PATH)).load(f'fx_rates_tickers_{account_type}', fmt='csv',
                                                                     prefix='')

        last_vol = df_volumes_tickers.drop(columns=['date']).iloc[-1]
        last_price = df_prices_tickers.drop(columns=['date']).iloc[-1]
        last_fx = df_fx_rates_tickers.drop(columns=['date']).iloc[-1]
        account_allocation = last_vol * last_price * last_fx
        return account_allocation

@register_widget("table")
class PieChartLogic(VariantWidgetLogic):
    def update_data(self):
        self.widget.data = {
            "columns": [
                "Col 1", "Col 2", "Col 3", "Col 4", "Col 5",
                "Col 6", "Col 7", "Col 8", "Col 9", "Col 10",
                "Col 11", "Col 12", "Col 13", "Col 14", "Col 15"
            ],
            "rows": [
                ["R1C1", "R1C2", "R1C3", "R1C4", "R1C5",
                 "R1C6", "R1C7", "R1C8", "R1C9", "R1C10",
                 "R1C11", "R1C12", "R1C13", "R1C14", "R1C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
                ["R2C1", "R2C2", "R2C3", "R2C4", "R2C5",
                 "R2C6", "R2C7", "R2C8", "R2C9", "R2C10",
                 "R2C11", "R2C12", "R2C13", "R2C14", "R2C15"],
            ]
        }

@register_widget('overview')
class OverviewLogic(BaseWidgetLogic):
    def update_data(self):
        widget_data = {}

        account_type = self.widget.config.get("account_type", "main")  # type: ignore

        if account_type == 'xtb_combined':
            account_types = ['main', 'ike', 'ikze']
        else:
            account_types = [account_type]

        limit = self.widget.config.get("limit", 0)  # type: ignore
        positions = Position.objects.filter(account_type__in=account_types, status="open")
        tickers = list(positions.values_list('symbol', flat=True).order_by('symbol').distinct())
        instruments = Instrument.objects.filter(symbol__in=tickers)
        instruments_info = {i.symbol: {'logo_url': i.logo_url} for i in instruments}

        portfolio_value = DataStore(Path(MARKET_DATA_PATH)).load(f'account_data_{account_type}', fmt='csv', prefix='')
        account_positions = DataStore(Path(MARKET_DATA_PATH)).load(f'account_positions_{account_type}', fmt='parquet',
                                                                   prefix='')

        profit = account_positions['gross_pl_pln'].sum()
        invested_value = account_positions['open_price_total_pln'].sum()
        current_value = account_positions['current_price_total_pln'].sum()
        free_funds = self._get_latest_values(portfolio_value['free_funds'])
        total_value = current_value + free_funds

        cagr = metrics.Metric.new_cagr_v3(invested_value, current_value, account_positions['date'].iloc[0])
        wcagr = metrics.Metric.new_weighted_cagr_v2(account_positions["open_price_total_pln"],
                                                    account_positions["current_price_total_pln"],
                                                    account_positions['holding_years'])
        twr_data = portfolio_value[['date', 'invested_value', 'portfolio_value']]
        twr = metrics.Metric.twr_v2(twr_data, time_period='total')
        periodic_metrics = {'D': metrics.Metric.twr_v2(twr_data, time_period='today'),
                            'W': metrics.Metric.twr_v2(twr_data, time_period='last_week'),
                            'M': metrics.Metric.twr_v2(twr_data, time_period='last_month')}

        hpr_data = pd.DataFrame({
            'start': account_positions.groupby(['symbol'])["open_price_total_pln"].sum(),
            'end': account_positions.groupby(['symbol'])["current_price_total_pln"].sum()
        })
        hpr = hpr_data['end'] / hpr_data['start'] - 1
        for ticker, info in instruments_info.items():
            info['hpr'] = float(hpr.get(ticker, 0.0))

        widget_data['total_value'] = total_value
        widget_data['profit'] = profit
        widget_data['free_funds'] = free_funds
        widget_data['instruments_info'] = instruments_info
        widget_data['metrics'] = {'cagr': cagr, 'wcagr': wcagr, 'twr': twr}
        widget_data['metrics_changes'] = periodic_metrics

        if limit > 0:
            progress_current, progress_current_pct = self._get_progress_amount(account_types, limit)
            widget_data['progress_current'] = progress_current
            widget_data['progress_current_pct'] = progress_current_pct

        self.widget.data = widget_data

        self.update_allocation()

    def update_allocation(self):
        """
        Fetches all OverviewWidget instances from the database,
        calculates the total portfolio value, and updates this widget's
        'allocation_perc' field inside self.data.
        """
        self.widget.data = self.widget.data or {}  # Ensure the widget's data exists

        if self.widget.config['account_type'] == "xtb_combined":
            self.widget.data["allocation_perc"] = 1.0
            return 1.0

        all_widgets = OverviewWidget.objects.filter(widget_type="overview").exclude(config__account_type="xtb_combined")

        total_all = 0.0
        for w in all_widgets:
            data = getattr(w, "data", {}) or {}
            total_all += data.get("total_value", 0.0)

        current_value = self.widget.data.get("total_value", 0.0)
        allocation_perc = current_value / total_all if total_all > 0 else 0.0

        self.widget.data["allocation_perc"] = allocation_perc

        return allocation_perc

    def _get_latest_values(self, df_prices):
        if isinstance(df_prices, pd.DataFrame):
            return df_prices.iloc[-1].to_dict()  # to_frame().T.reset_index(drop=True)
        return df_prices.iloc[-1]

    def _get_progress_amount(self, account_types, limit):
        progress_current = (
                CashOperation.objects.filter(account_type__in=account_types, type__iendswith="Deposit")
                .aggregate(total=Sum('amount'))['total'] or 0
        )
        progress_current_pct = progress_current / limit
        return progress_current, progress_current_pct
