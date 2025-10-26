from collections import defaultdict
import pandas as pd
import os
from datetime import datetime, timedelta

from core.logger import logger
import yfinance as yf


def get_tickers_to_download(tickers, ticker_mapping, etf_currency_mapping):
    tickers_to_download = [key for key, val in ticker_mapping.items() if val in tickers]
    fx_needed = {
        f"{cur}PLN=X"
        for cur in set(etf_currency_mapping[t] for t in tickers)
        if cur != "PLN"
    }
    tickers_to_download += list(fx_needed)
    return tickers_to_download


def group_tickers_by_currency(tickers, etf_currency_mapping):
    currency_groups = defaultdict(list)
    for ticker in tickers:
        currency = etf_currency_mapping.get(ticker, "USD")
        currency_groups[currency].append(ticker)
    return currency_groups


def get_currency_for_ticker(ticker, currency_groups):
    base_currency = next((cur for cur, syms in currency_groups.items() if ticker in syms), None)
    if base_currency is None:
        raise ValueError(f"Ticker {ticker} not found in currency_groups")
    return base_currency


def convert_prices_to_pln(df_prices_tickers, df_fx, currency_groups):
    """
    Convert ticker prices from their base currencies to PLN using FX rates.

    Parameters
    ----------
    df_prices_tickers : pd.DataFrame
        DataFrame with instrument prices (columns = tickers).
    df_fx : pd.DataFrame
        DataFrame with FX rates to PLN (e.g., USDPLN, EURPLN).
    currency_groups : dict
        Mapping of base currency to list of tickers (e.g., {'USD': [...], 'EUR': [...], 'PLN': [...]}).

    Returns
    -------
    df_price_pln : pd.DataFrame
        DataFrame with all ticker prices converted to PLN.
    """
    df_price_pln = pd.DataFrame(index=df_prices_tickers.index)

    for currency, tickers_in_currency in currency_groups.items():
        if currency == "PLN":
            # No FX conversion needed
            df_price_pln[tickers_in_currency] = df_prices_tickers[tickers_in_currency]
        else:
            fx_pair = f"{currency}PLN"
            if fx_pair not in df_fx.columns:
                raise ValueError(f"Missing FX rate column for {fx_pair} in df_fx")

            df_price_pln[tickers_in_currency] = (df_prices_tickers[tickers_in_currency].mul(df_fx[fx_pair], axis=0))

    return df_price_pln


def fetch_market_data(tickers, ticker_mapping, period, start_date, snapshot_path):
    # === Load existing data ===

    if os.path.exists(snapshot_path):
        df_prices = pd.read_csv(snapshot_path)
        df_prices["Date"] = pd.to_datetime(df_prices["Date"])
        df_prices = df_prices.set_index("Date")
    else:
        df_prices = pd.DataFrame()

    today = datetime.now().date()
    last_date = df_prices.index[-1].date() if not df_prices.empty else None
    # todo: test 00:00 AM and 09:00 AM
    if (0 <= datetime.now().hour < 10) and (not df_prices.empty):
        last_date -= timedelta(days=1)

    # === Determine start date ===
    if last_date is None:
        fetch_from = start_date
    elif last_date < today:
        fetch_from = last_date
    else:
        fetch_from = today

    # todo: (1h 2025-10-24 -> 2025-10-23 23:17:19+01:00) (Yahoo error = "Invalid input - start date cannot be after end date. startDate = 1761260400, endDate = 1761257839")')
    df_new = yf.download(tickers, interval=period, start=fetch_from, auto_adjust=True)['Close']

    if period in ('1h', '30m'):  # Hourly data from yfinance is localized to UTC, daily is not localized
        df_new.index.name = "Date"
        df_new.index = df_new.index.tz_convert('Europe/Warsaw').tz_localize(None)  # Convert to UTC+2

    df_new.rename(columns=ticker_mapping, inplace=True)
    df_new = df_new.ffill().bfill()

    # === Combine old and new data ===
    if not df_new.empty:
        logger.info(f'New data downloaded: {df_new.index[0]} - {df_new.index[-1]} ({tickers}).')
        df_prices = pd.concat([df_prices, df_new])
        df_prices = df_prices[~df_prices.index.duplicated(keep="last")].sort_index()
    else:
        logger.info(f'No new data to download.')

    df_prices.to_csv(snapshot_path)
    return df_prices
