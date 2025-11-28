import pandas as pd
from pathlib import Path
from datetime import datetime

from investments.models import Position, Instrument, CashOperation
from investments.services.valuation.datetime_utils import standardize_datetime_by_period
from investments.constants import MARKET_DATA_PATH, MARKET_DATA_FILENAME
from core.datastore import DataStore


class PortfolioEngine:
    def __init__(self, adj=0.995):
        """
        df_prices: hourly price DataFrame with DateTimeIndex named 'date'
        columns include instrument symbols and FX columns like 'USDPLN', 'EURPLN', ...
        """
        self.market_data_path = MARKET_DATA_PATH
        self.market_data_filename = MARKET_DATA_FILENAME
        self.accounts = ['main', 'ike', 'ikze', 'xtb_combined', 'usd']
        self.df_prices = self._get_prices_df()
        self.adj = adj
        self.full_index = self.df_prices.index.rename("date")

        # FX columns (ending with PLN)
        self.fx_cols = self.df_prices.filter(like="PLN").columns.tolist()
        # map currency -> fx column name, e.g. 'USD' -> 'USDPLN'
        self.currency_to_fx = {fx[:-3]: fx for fx in self.fx_cols}
        self.currency_to_fx["PLN"] = None

        # pre-slice fx frame
        self.df_fx_rates = self.df_prices[self.fx_cols].copy() if self.fx_cols else pd.DataFrame(index=self.full_index)

    def entry_point(self):
        for account in self.accounts:
            self.get_account_data(account)
        # self.df_prices = df_prices

        # for account in accounts:
        #     get_account_data(accounts)

    def get_account_data(self, account_type):
        df_prices = self._get_prices_df()

        if account_type == 'xtb_combined':
            account_types = ['main', 'ike', 'ikze']
        else:
            account_types = [account_type]

        positions = Position.objects.filter(account_type__in=account_types, status="open")
        df_positions = pd.DataFrame(list(positions.values('open_time', 'symbol', 'open_price', 'volume')))
        account_positions = self._prepare_positions(df_positions)

        tickers = list(positions.values_list('symbol', flat=True).order_by('symbol').distinct())
        instruments = Instrument.objects.filter(symbol__in=tickers)
        currency_map = {i.symbol: i.currency for i in instruments}

        current_prices = self._get_latest_values(df_prices)

        # keep building account_positions-derived columns (current_fx_rate, current_value etc)
        account_positions["currency"] = account_positions["symbol"].map(currency_map)
        account_positions["fx_symbol"] = account_positions["currency"] + "PLN"
        account_positions['current_fx_rate'] = account_positions["fx_symbol"].map(current_prices).fillna(1.0)

        # We need open_fx_rate (historical fx) from df_fx_rates melted join like before:
        # fx_cols = df_prices.filter(like='PLN').columns.tolist()
        # df_fx_rates = df_prices[fx_cols].copy()
        df_fx_melted = self.df_fx_rates.reset_index().rename(columns={'Date': 'date'}).melt(
            id_vars='date', var_name='fx_symbol', value_name='open_fx_rate'
        )

        account_positions = account_positions.merge(df_fx_melted, how='left', on=['date', 'fx_symbol'])

        account_positions["current_price_total"] = account_positions["symbol"].map(current_prices) * account_positions["volume"]
        account_positions["current_price_total_pln"] = account_positions["current_price_total"] * account_positions['current_fx_rate'] * self.adj
        account_positions["open_price_total_pln"] = account_positions["open_price_total"] * account_positions["open_fx_rate"] * (1 / self.adj)
        account_positions['gross_pl_pln'] = account_positions["current_price_total_pln"] - account_positions["open_price_total_pln"]
        account_positions['holding_years'] = (datetime.now() - account_positions['date']).dt.total_seconds() / (365.25 * 24 * 3600)

        DataStore(Path(self.market_data_path)).save(f'account_positions_{account_type}', account_positions, fmt='parquet',prefix='')

        # Build time matrices and save them for Widget Y (but DO NOT compute account_allocation here)
        df_volumes_tickers, df_prices_tickers, df_fx_rates_tickers = self._build_time_matrices(account_positions, currency_map)

        DataStore(Path(self.market_data_path)).save(f'volumes_tickers_{account_type}', df_volumes_tickers.reset_index(),fmt='csv', prefix='')
        DataStore(Path(self.market_data_path)).save(f'prices_tickers_{account_type}', df_prices_tickers.reset_index(), fmt='csv', prefix='')
        DataStore(Path(self.market_data_path)).save(f'fx_rates_tickers_{account_type}', df_fx_rates_tickers.reset_index(), fmt='csv', prefix='')

        portfolio_value = pd.DataFrame()
        portfolio_value['invested_value'] = account_positions.groupby("date")["open_price_total_pln"].sum().reindex(self.full_index).fillna(0).cumsum()
        portfolio_value['portfolio_value'] = (df_volumes_tickers * df_prices_tickers * df_fx_rates_tickers).sum(axis=1) * self.adj
        portfolio_value['free_funds'] = self._get_cash_cumulative_df(account_types, '1h').reindex(portfolio_value.index, method='ffill').fillna(0)
        portfolio_value['total_portfolio_value'] = portfolio_value['portfolio_value'] + portfolio_value['free_funds']

        DataStore(Path(self.market_data_path)).save(f'account_data_{account_type}', portfolio_value.reset_index(), fmt='csv', prefix='')

    def _prepare_positions(self, df_positions):
        """Normalize and aggregate raw positions dataframe (open_time, symbol, open_price, volume)."""
        df_positions['open_time'] = standardize_datetime_by_period(df_positions['open_time'], '1h')
        df_positions['open_time'] = df_positions['open_time'].dt.ceil('h')
        df_positions = df_positions.rename(columns={"open_time": "date"})
        df_positions["date"] = pd.to_datetime(df_positions["date"])
        df_positions = df_positions.set_index("date").sort_index().reset_index()
        df_positions["open_price_total"] = df_positions["open_price"] * df_positions["volume"]
        df_positions["volume_cumsum"] = df_positions.sort_index().groupby("symbol")["volume"].cumsum()

        account_positions = (
            df_positions.groupby(["date", "symbol"]).agg(
                open_price_total=("open_price_total", "sum"),
                volume=("volume", "sum"),
                volume_cumulative=("volume_cumsum", "last"),
            )
        ).reset_index()

        return account_positions

    def _build_time_matrices(self, account_positions, currency_map):
        """
        Builds:
            - df_volumes_tickers : cumulative volumes per symbol over full_index
            - df_prices_tickers  : prices for those symbols reindexed to full_index
            - df_fx_rates_tickers: fx rate per symbol reindexed to full_index
        Returns (df_volumes_tickers, df_prices_tickers, df_fx_rates_tickers)
        """
        # volumes pivot, reindex to full grid
        df_volumes_tickers = account_positions.pivot_table(
            index="date", columns="symbol", values="volume_cumulative", aggfunc="last"
        )

        df_volumes_tickers = df_volumes_tickers.reindex(self.full_index).ffill().fillna(0)

        # prices for the symbols
        symbols = df_volumes_tickers.columns.tolist()
        df_prices_tickers = self.df_prices.reindex(self.full_index)[symbols].ffill()

        # fx per symbol
        df_fx_rates_tickers = pd.DataFrame(
            {s: (self.df_fx_rates[self.currency_to_fx[curr]]
                 if self.currency_to_fx.get(curr)
                 else pd.Series(1.0, index=self.full_index))
             for s, curr in currency_map.items()}, index=self.full_index
        )

        return df_volumes_tickers, df_prices_tickers, df_fx_rates_tickers

    def compute_account_allocation_from_matrices(self, df_volumes_tickers, df_prices_tickers, df_fx_rates_tickers):
        """Compute account_allocation vector from final-row of matrices."""
        last_vol = df_volumes_tickers.iloc[-1]
        last_price = df_prices_tickers.iloc[-1]
        last_fx = df_fx_rates_tickers.iloc[-1]
        account_allocation = last_vol * last_price * last_fx
        return account_allocation

    def _get_prices_df(self):
        df_prices = DataStore(Path(self.market_data_path)).load(self.market_data_filename, fmt='parquet', prefix='')
        return df_prices

    def _get_cash_cumulative_df(self, account_types, period):
        cash_ops = CashOperation.objects.filter(account_type__in=account_types)
        df_cash_ops = pd.DataFrame(cash_ops.values('time', 'amount'))
        df_cash_ops['time'] = standardize_datetime_by_period(df_cash_ops['time'], period)
        cash_cumulative_df = (
            df_cash_ops.groupby('time')['amount']
            .sum()
            .cumsum()
        )
        return cash_cumulative_df

    def _get_latest_values(self, df_prices):
        if isinstance(df_prices, pd.DataFrame):
            return df_prices.iloc[-1].to_dict()  # to_frame().T.reset_index(drop=True)
        return df_prices.iloc[-1]
