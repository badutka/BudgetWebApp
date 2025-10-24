import pandas as pd
from datetime import datetime

from .market_data import group_tickers_by_currency, get_tickers_to_download, convert_prices_to_pln, fetch_market_data
from .volume import get_cumulative_volume
from .cashflow import free_funds_over_time
from .invested_capital import get_cumulative_input_value
from .metrics import Metric

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
    df_prices = fetch_market_data(tickers_to_download, TICKER_MAPPING, period, start_date, file_path)

    df_cumvol = get_cumulative_volume(df_positions, tickers, period, df_prices.index)

    # df_positions open_time gets converted to hour ceil(), inside get_cumulative_input_value function
    input_value, input_value_cumsum = get_cumulative_input_value(df_positions, tickers, period, df_prices, currency_groups)

    df_price_pln = convert_prices_to_pln(df_prices, currency_groups) * 0.995
    instruments_value = df_cumvol[tickers] * df_price_pln[tickers]

    portfolio_value = instruments_value.sum(axis=1)
    free_funds = free_funds_over_time(account_type, period)
    free_funds = free_funds.reindex(portfolio_value.index, method='ffill').fillna(0)
    total_portfolio_value = portfolio_value + free_funds

    # logger.debug(df_positions)
    # df_positions = df_positions[(df_positions['open_time'].isin(['2024-08-14 17:00:00', '2024-08-20 10:00:00', '2024-08-20 16:00:00']))]

    df_positions_cagr = pd.DataFrame()
    # These need to be stacked vertically, to calculate a new column for hold time for all positions.
    for ticker in tickers:
        df_ticker = df_positions[df_positions['symbol'] == ticker].copy()
        df_ticker['open_price_total'] = df_ticker['open_price'] * df_ticker['volume']
        df_ticker = df_ticker[['open_time', 'open_price_total', 'volume']].set_index('open_time')

        base_currency = None
        for currency, symbols in currency_groups.items():
            if ticker in symbols:
                base_currency = currency
                break
        if base_currency is None:
            raise ValueError(f"Ticker {ticker} not found in currency_groups")

        df_ticker = df_ticker.merge(df_prices[[f'{base_currency}PLN', ticker]], left_index=True, right_index=True, how='left')
        # df_ticker.columns = [f'current_price' if column == ticker else column for column in df_ticker.columns]
        df_ticker['open_price_total_pln'] = df_ticker['open_price_total'] * df_ticker[f'{base_currency}PLN']
        df_ticker['holding_years'] = (datetime.now() - df_ticker.index).total_seconds() / (365.25 * 24 * 3600)
        # df_ticker['current_price_total_pln'] = df_ticker['current_price'] * df_ticker[f'{base_currency}PLN']
        df_ticker['gross_pl'] = df_price_pln[ticker].iloc[-1] * df_ticker['volume'] - df_ticker['open_price_total_pln']
        df_positions_cagr = pd.concat([df_positions_cagr, df_ticker[['open_price_total_pln', 'gross_pl', 'holding_years']]])

    # df_positions_cagr = df_positions_cagr.sort_index()
    # # logger.debug(df_positions_cagr)
    # # df_positions_cagr = df_positions_cagr[(df_positions_cagr.index.isin(['2024-08-14 17:00:00', '2024-08-20 10:00:00', '2024-08-20 17:00:00']))]
    # test_new_weighted_cagr = Metric.new_weighted_cagr(df_positions_cagr)
    # logger.debug(f'{test_new_weighted_cagr = }')

    df_portfolio_over_time = pd.DataFrame({
        'input_value': input_value,
        'input_value_cumsum': input_value_cumsum,
        'portfolio_value': portfolio_value,
        'free_funds': free_funds,
        'total_portfolio_value': total_portfolio_value
    })

    (DataStore(base_dir="../artifacts/portfolio_snapshots")
     .save(f"portfolio_over_time_{account_type}", df_portfolio_over_time, fmt='csv', index=True, prefix=''))

    logger.info(f"Portfolio valuation complete. Date range: 2024-07-22 - {datetime.now().strftime('%Y-%m-%d')}.")
    return df_portfolio_over_time
