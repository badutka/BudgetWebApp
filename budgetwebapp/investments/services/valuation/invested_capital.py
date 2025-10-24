import pandas as pd

from .datetime_utils import standardize_datetime_by_period
from core.logger import logger


def get_cumulative_input_value(df_positions, tickers, period, df_prices, currency_groups):
    df_input_value = pd.DataFrame(index=df_prices.index)

    for ticker in tickers:
        df_positions['open_time'] = standardize_datetime_by_period(df_positions['open_time'], period)
        if period in ['1h', '30m']:
            df_positions['open_time'] = df_positions['open_time'].dt.ceil('h')

        df_ticker = df_positions[df_positions['symbol'] == ticker].copy()
        df_ticker['usd_value'] = df_ticker['open_price'] * df_ticker['volume']
        df_ticker = df_ticker[['open_time', 'usd_value']].set_index('open_time')

        base_currency = None
        for currency, symbols in currency_groups.items():
            if ticker in symbols:
                base_currency = currency
                break
        if base_currency is None:
            raise ValueError(f"Ticker {ticker} not found in currency_groups")

        df_ticker = df_ticker.merge(df_prices[f'{base_currency}PLN'], left_index=True, right_index=True, how='left')

        df_ticker['pln_value'] = df_ticker['usd_value'] * df_ticker[f'{base_currency}PLN']
        df_ticker = df_ticker.groupby('open_time', as_index=True)['pln_value'].sum()
        df_input_value[ticker] = df_ticker

    df_input_value = df_input_value.fillna(0)

    df_input_value['total_pln'] = df_input_value.sum(axis=1)
    df_input_value['total_pln_cumulative'] = df_input_value['total_pln'].cumsum()
    # df_input_value_cumulative = df_input_value.sum(axis=0)
    return df_input_value['total_pln'], df_input_value['total_pln_cumulative']
