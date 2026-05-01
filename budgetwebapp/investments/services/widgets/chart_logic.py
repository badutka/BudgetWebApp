import pandas as pd
from pathlib import Path
from django.db.models import Sum

from budgetwebapp.investments.models import Position, Instrument, CashOperation
from budgetwebapp.investments.services.valuation import metrics
from budgetwebapp.investments.constants import MARKET_DATA_PATH
from core.datastore import DataStore
from core.logger import logger

from .registry import register_widget, register_dataset, load_dataset


# cache_key = f"widget:{dw.id}:{hash(filters)}"

@register_dataset("account_allocation")
def load_account_allocation_data(account=None):
    df_volumes_tickers = DataStore(Path(MARKET_DATA_PATH)).load(f'volumes_tickers_{account}', fmt='csv', prefix='')
    df_prices_tickers = DataStore(Path(MARKET_DATA_PATH)).load(f'prices_tickers_{account}', fmt='csv', prefix='')
    df_fx_rates_tickers = DataStore(Path(MARKET_DATA_PATH)).load(f'fx_rates_tickers_{account}', fmt='csv', prefix='')

    last_vol = df_volumes_tickers.drop(columns=['date']).iloc[-1]
    last_price = df_prices_tickers.drop(columns=['date']).iloc[-1]
    last_fx = df_fx_rates_tickers.drop(columns=['date']).iloc[-1]
    return last_vol * last_price * last_fx


@register_dataset("portfolio_total_value")
def load_portfolio_total_value():
    accounts = ['main', 'ike', 'ikze', 'usd']
    grand_total = 0.0

    for acc in accounts:
        df = DataStore(Path(MARKET_DATA_PATH)).load(f'account_data_{acc}', fmt='csv', prefix='')
        if not df.empty:
            grand_total += df['portfolio_value'].iloc[-1]

    return grand_total


@register_dataset("pie_chart_default")
def load_pie_chart_default_data(account=None):
    return {
        'labels': ['pie_chart_default'],
        'values': [111]
    }


@register_dataset("account_over_time")
def load_account_over_time_data(account=None):
    df_account_over_time = DataStore(Path(MARKET_DATA_PATH)).load(f'account_data_{account}', fmt='csv', prefix='')
    df_account_over_time = df_account_over_time.to_dict(orient='list')

    sample = 6

    if type(df_account_over_time['date'][0]) is not str:
        logger.debug("Casting time series date to str")
        df_account_over_time['date'] = [str(d) for d in df_account_over_time['date']]

    return {
        "date": df_account_over_time["date"][::sample],
        "series": {
            'invested_value': df_account_over_time['invested_value'][::sample],
            'portfolio_value': df_account_over_time['portfolio_value'][::sample],
            "net_gain": list(
                pd.Series(df_account_over_time["portfolio_value"][::sample])
                - pd.Series(df_account_over_time["invested_value"][::sample])
            ),
            "portfolio_value_2": list(pd.Series(df_account_over_time["portfolio_value"][::sample]) * 0.3),
            "portfolio_value_3": list(pd.Series(df_account_over_time["portfolio_value"][::sample]) * 0.5)
        },
        # optional custom names (can add later)
        "series_meta": {
            "invested_value": {"name": "Invested Value"},
            "portfolio_value": {"name": "Total Value"},
            "portfolio_value_2": {"name": "Invested Value 2"},
            "portfolio_value_3": {"name": "Invested Value 3"},
            "net_gain": {"name": "Net Gain"},
        }
    }


class BaseWidgetLogic:
    def __init__(self, widget):
        self.widget = widget

    def update_data(self):
        raise NotImplementedError


@register_widget("chart", 'timeseries')
class TimeSeriesChartLogic(BaseWidgetLogic):
    def update_data(self):
        account_type = self.widget.config.get("account_type", "main")

        # self.widget.data = load_account_over_time_data(account=account_type)
        return load_account_over_time_data(account=account_type)


@register_widget("chart", 'pie')
class PieChartLogic(BaseWidgetLogic):
    def update_data(self):
        account_type = self.widget.config.get("account_type", "main")
        dataset_name = self.widget.config.get("dataset")
        data = load_dataset(name=dataset_name, account=account_type)

        # self.widget.data = {
        return {
            "labels": data.index.tolist(),
            "values": data.values.round(2).tolist()
        }


@register_widget("table")
class TableLogic(BaseWidgetLogic):
    def update_data(self):
        return {
            "columns": [
                "Col 1", "Col 2", "Col 3"
            ],
            "rows": [
                ["R1C1", "R1C2", "R1C3"],
                ["R1C1", "R1C2", "R1C3"],
                ["R1C1", "R1C2", "R1C3"],
                ["R1C1", "R1C2", "R1C3"],
                ["R1C1", "R1C2", "R1C3"],
                ["R1C1", "R1C2", "R1C3"],
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

        widget_data["allocation_perc"] = self._update_allocation(widget_data, self.widget.config)

        return widget_data
        # self.widget.data = widget_data

        # self.update_allocation()

    def _update_allocation(self, widget_data, widget_config):
        """
        Fetches all OverviewWidget instances from the database,
        calculates the total portfolio value, and updates this widget's
        'allocation_perc' field inside self.data.
        """
        widget_data = widget_data or {}  # Ensure the widget's data exists

        if widget_config['account_type'] == "xtb_combined":
            return 1.0

        total_portfolio_value = load_dataset("portfolio_total_value")
        current_value = widget_data.get("total_value", 0.0)

        allocation_perc = current_value / total_portfolio_value

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
