import pandas as pd
from .datetime_utils import standardize_datetime_by_period
from core.logger import logger


def get_cumulative_volume(df_positions, tickers, period, index):
    df_cumvol = pd.DataFrame(index=index)
    for ticker in tickers:
        df_positions['open_time'] = standardize_datetime_by_period(df_positions['open_time'], period)
        df_sym = (
            df_positions[df_positions['symbol'] == ticker]
            .groupby('open_time')['volume']
            .sum()
            .sort_index()
        )
        cum_vol = df_sym.cumsum().reindex(index, method='ffill').fillna(0)
        df_cumvol[ticker] = cum_vol

    return df_cumvol
