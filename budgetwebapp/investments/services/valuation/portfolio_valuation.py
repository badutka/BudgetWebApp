import pandas as pd
from datetime import datetime

from .market_data import group_tickers_by_currency, get_tickers_to_download, convert_prices_to_pln, download_market_data
from .volume import get_cumulative_volume
from .cashflow import free_funds_over_time
from .invested_capital import get_cumulative_input_value

from core.datastore import DataStore
from core.logger import logger


def get_positions_value_over_time(positions, account_type, tickers, period, start_date='2024-07-22'):
    TICKER_MAPPING = {
        "VUAA.L": "VUAA.UK",
        "CNDX.L": "CNDX.UK",
        "IGLN.L": "IGLN.UK",
        "IUIT.L": "IUIT.UK",
        "SPYL.DE": "SPYL.DE",
        "USDPLN=X": "USDPLN",
        "EURPLN=X": "EURPLN",
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

    df_positions = pd.DataFrame({
        'symbol': [p.symbol for p in positions],
        'volume': [p.volume for p in positions],
        'open_time': [p.open_time for p in positions],
        'open_price': [p.open_price for p in positions]
        # p.open_time.date() can be use instead of df_sym.index.tz_localize
    })

    # start_date = positions.earliest('open_time').open_time.date()
    file_path = f'../artifacts/portfolio_snapshots/df_prices_{account_type}_{period}.csv'
    df_prices = download_market_data(tickers_to_download, TICKER_MAPPING, period, start_date, file_path)

    df_cumvol = get_cumulative_volume(df_positions, tickers, period, df_prices.index)
    input_value_over_time = get_cumulative_input_value(df_positions, tickers, period, df_prices, currency_groups)
    df_price_pln = convert_prices_to_pln(df_prices, currency_groups)
    instruments_value = df_cumvol[tickers] * df_price_pln[tickers]

    portfolio_value = instruments_value.sum(axis=1)
    free_funds = free_funds_over_time(account_type, period)
    free_funds = free_funds.reindex(portfolio_value.index, method='ffill').fillna(0)
    total_portfolio_value = portfolio_value + free_funds

    df_portfolio_over_time = pd.DataFrame({
        'input_value_over_time': input_value_over_time,
        'portfolio_value': portfolio_value,
        'free_funds': free_funds,
        'total_portfolio_value': total_portfolio_value
    })

    (DataStore(base_dir="../artifacts/portfolio_snapshots")
     .save(f"portfolio_over_time_{account_type}", df_portfolio_over_time, fmt='csv', index=True, prefix=''))

    logger.info(f"Portfolio valuation complete. Date range: 2024-07-22 - {datetime.now().strftime('%Y-%m-%d')}.")
    return df_portfolio_over_time
