import pandas as pd
from datetime import datetime

from investments.models import CashOperation
from .market_data import (group_tickers_by_currency, get_tickers_to_download, fetch_market_data,
                          convert_prices_to_pln, get_currency_for_ticker)
from .volume import get_cumulative_volume
from .datetime_utils import standardize_datetime_by_period
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

    currencies = list(set([f'{currency}PLN' for currency in ETF_CURRENCY.values()]))
    currency_groups = group_tickers_by_currency(tickers, ETF_CURRENCY)
    tickers_to_download = get_tickers_to_download(tickers, TICKER_MAPPING, ETF_CURRENCY)

    df_positions = pd.DataFrame({
        'symbol': [p.symbol for p in positions],
        'volume': [p.volume for p in positions],
        'open_time': [p.open_time for p in positions],
        'open_price': [p.open_price for p in positions]
        # p.open_time.date() can be use instead of df_sym.index.tz_localize
    })

    file_path = f'../artifacts/portfolio_snapshots/df_prices_{account_type}_{period}.csv'
    df_prices = fetch_market_data(tickers_to_download, TICKER_MAPPING, period, start_date, file_path)

    df_cumvol = get_cumulative_volume(df_positions, tickers, period, df_prices.index)

    # These are reindex with market series, to calculate value at each increment (req: TWR)
    df_input_value = pd.DataFrame(index=df_prices.index)

    # These need to be stacked vertically, to calculate a new column for hold time for all positions. (req: CAGR)
    df_positions_cagr = pd.DataFrame()

    for ticker in tickers:
        base_currency = get_currency_for_ticker(ticker, currency_groups)
        df_ticker = prepare_ticker_series(
            df_positions['symbol'],
            df_positions['open_time'],
            df_positions['open_price'],
            df_positions['volume'],
            ticker,
            df_prices[ticker],
            df_prices[f'{base_currency}PLN'],
            base_currency,
            period
        )
        # logger.debug(df_ticker)
        # The smallest available granularity for ticker prices and FX rates is 1 hour, so positions are aggregated.
        # If two positions are opened 15 minutes apart, they will share the same FX rate
        # and have the same calculated holding time before grouping. Hence in this case, grouping reduces
        # number of rows and ensured uniqueness of index, without the loss of data (per position data).
        ticker_series = df_ticker.groupby(df_ticker.index)['open_price_total_pln'].sum()
        df_input_value[ticker] = ticker_series

        # Vertically stacking data for CAGR; Usually CAGR metrics will require no grouping (separate positions)
        # But since the lowest granularity is currently 1h, these can be grouped by the hourly index.
        # todo: consider grouping
        df_ticker['holding_years'] = (datetime.now() - df_ticker.index).total_seconds() / (365.25 * 24 * 3600)
        df_positions_cagr = pd.concat(
            [df_positions_cagr, df_ticker[['open_price_total_pln', 'gross_pl', 'holding_years']]])
        # df_positions_cagr = pd.concat([df_positions_cagr, df_ticker])

        cum_vol_grouped = df_ticker.groupby(df_ticker.index)['cum_volume'].last()
        df_cumvol[ticker] = cum_vol_grouped.reindex(df_prices.index, method='ffill').fillna(0)

    df_positions_cagr = df_positions_cagr.sort_index()

    df_input_value = df_input_value.fillna(0)
    df_input_value['total_pln'] = df_input_value.sum(axis=1)
    df_input_value['total_pln_cumulative'] = df_input_value['total_pln'].cumsum()

    df_prices_pln = convert_prices_to_pln(df_prices[tickers], df_prices[currencies], currency_groups) * 0.995
    instruments_value = df_cumvol[tickers] * df_prices_pln[tickers]
    portfolio_value = instruments_value.sum(axis=1)

    free_funds = free_funds_over_time(account_type, period)
    free_funds = free_funds.reindex(portfolio_value.index, method='ffill').fillna(0)

    # df_positions_cagr = df_positions_cagr.sort_index()
    # logger.info(df_positions_cagr)
    # test_new_weighted_cagr = Metric.new_weighted_cagr(df_positions_cagr)
    # logger.debug(f'{test_new_weighted_cagr = }')

    df_portfolio_over_time = pd.DataFrame({
        'input_value': df_input_value['total_pln'].copy(),
        'input_value_cumsum': df_input_value['total_pln_cumulative'].copy(),
        'portfolio_value': portfolio_value,
        'free_funds': free_funds,
        'total_portfolio_value': portfolio_value + free_funds
    })

    (DataStore(base_dir="../artifacts/portfolio_snapshots")
     .save(f"portfolio_over_time_{account_type}", df_portfolio_over_time, fmt='csv', index=True, prefix=''))

    logger.info(f"Portfolio valuation complete. Date range: 2024-07-22 - {datetime.now().strftime('%Y-%m-%d')}.")
    return df_portfolio_over_time


def free_funds_over_time(account_type, period):
    cash_ops = CashOperation.objects.filter(account_type=account_type)
    df_cash_ops = pd.DataFrame({
        'time': [d.time for d in cash_ops],
        'amount': [d.amount for d in cash_ops]
    })
    df_cash_ops['time'] = standardize_datetime_by_period(df_cash_ops['time'], period)
    df_cumulative_cash = (
        df_cash_ops.groupby('time')['amount']
        .sum()
        .cumsum()
    )
    return df_cumulative_cash


def prepare_ticker_series(
        symbol_series,  # e.g., df_positions['symbol']
        open_time_series,  # e.g., df_positions['open_time']
        open_price_series,  # e.g., df_positions['open_price']
        volume_series,  # e.g., df_positions['volume']
        ticker,  # current ticker
        price_series,  # df_prices[ticker]
        currency_rate_series,  # df_prices[f'{base_currency}PLN']
        base_currency,  # e.g. USDPLN
        period=None,
        adj=0.995
):
    # --- Step 1: Filter positions for this ticker ---
    mask = (symbol_series == ticker)
    open_times = open_time_series[mask].copy()
    open_prices = open_price_series[mask].copy()
    volumes = volume_series[mask].copy()

    # --- Step 2: Standardize datetime (if applicable) --
    if period is not None:
        open_times = standardize_datetime_by_period(open_times, period)
        if period in ['1h', '30m']:
            open_times = open_times.dt.ceil('h')

    # --- Step 3: Construct base DataFrame ---
    df_ticker = pd.DataFrame({
        'open_time': open_times,
        'open_price': open_prices,
        'volume': volumes
    }).set_index('open_time').sort_index()

    # --- Step 4: Merge FX rate series ---
    df_ticker = df_ticker.merge(currency_rate_series, left_index=True, right_index=True, how='left')
    df_ticker = df_ticker.merge(price_series, left_index=True, right_index=True, how='left')
    fx_col = f'{base_currency}PLN'

    # --- Step 5: Derived columns ---
    df_ticker['open_price_total'] = df_ticker['open_price'] * df_ticker['volume']
    # open_price comes from XTB data, but yfinance data could be used instead:
    # df_ticker['open_price_total'] = price_series.reindex(df_ticker.index, method='ffill') * df_ticker['volume']
    df_ticker['open_price_total_pln'] = df_ticker['open_price_total'] * df_ticker[fx_col]

    # Latest prices for gross P/L
    latest_price = price_series.iloc[-1]
    latest_fx = currency_rate_series.iloc[-1]

    df_ticker['gross_pl'] = latest_price * df_ticker['volume'] * latest_fx * adj - df_ticker['open_price_total_pln']
    df_ticker['cum_volume'] = df_ticker['volume'].cumsum()

    return df_ticker
