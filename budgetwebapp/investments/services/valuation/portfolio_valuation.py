import pandas as pd
import yfinance as yf
from collections import defaultdict
from investments.models import Position, CashOperation
from datetime import datetime

from .market_data import group_tickers_by_currency, get_tickers_to_download, convert_prices_to_pln
from .volume import get_cumulative_volume
from .cashflow import free_funds_over_time
from .invested_capital import get_cumulative_input_value
from core.datastore import DataStore

from core.logger import logger


def get_positions_value_over_time(account_type, instrument_types, tickers, period, start_date='2024-07-22'):
    TICKER_MAPPING = {
        "VUAA.L": "VUAA.UK",
        "CNDX.L": "CNDX.UK",
        "IGLN.L": "IGLN.UK",
        "IUIT.L": "IUIT.UK",
        "SPYL.DE": "SPYL.DE",
        "USDPLN=X": "USDPLN",
        "EURPLN=X": "EURPLN"
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

    positions = Position.objects.filter(
        account_type=account_type,
        instrument_type__in=instrument_types
    )

    df_positions = pd.DataFrame({
        'symbol': [p.symbol for p in positions],
        'volume': [p.volume for p in positions],
        'open_time': [p.open_time for p in positions],
        'open_price': [p.open_price for p in positions]
        # p.open_time.date() can be use instead of df_sym.index.tz_localize
    })

    # start_date = positions.earliest('open_time').open_time.date()

    df_prices = yf.download(tickers_to_download, interval=period, start=start_date, auto_adjust=True)['Close']

    if period in ('1h', '30m'):
        # Hourly data from yfinance is localized to UTC, daily is not localized
        # Convert to UTC+2
        df_prices.index = df_prices.index.tz_convert('Europe/Warsaw').tz_localize(None)

    df_prices.rename(columns=TICKER_MAPPING, inplace=True)
    df_prices = df_prices.ffill().bfill()

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
     .save("portfolio_over_time", df_portfolio_over_time, fmt='csv', index=True, prefix=''))

    logger.info(f"Portfolio valuation complete. Date range: 2024-07-22 - {datetime.now().strftime('%Y-%m-%d')}.")
    return df_portfolio_over_time
