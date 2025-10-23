from collections import defaultdict
import pandas as pd
import os
from datetime import datetime

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


def convert_prices_to_pln(df_prices, currency_groups):
    df_price_pln = pd.DataFrame(index=df_prices.index)
    for currency, tickers_in_currency in currency_groups.items():
        if currency == "PLN":
            df_price_pln[tickers_in_currency] = df_prices[tickers_in_currency]
        else:
            fx_pair = f"{currency}PLN"
            if fx_pair not in df_prices.columns:
                raise ValueError(f"Missing FX rate column for {fx_pair}")
            df_price_pln[tickers_in_currency] = df_prices[tickers_in_currency].mul(df_prices[fx_pair], axis=0)
    return df_price_pln


def download_market_data(tickers, ticker_mapping, period, start_date, snapshot_path):
    # === Load existing data ===

    if os.path.exists(snapshot_path):
        df_prices = pd.read_csv(snapshot_path)
        df_prices["Date"] = pd.to_datetime(df_prices["Date"])
        df_prices = df_prices.set_index("Date")
    else:
        df_prices = pd.DataFrame()

    today = datetime.now().date()
    last_date = df_prices.index[-1].date() if not df_prices.empty else None

    # === Determine start date ===
    if last_date is None:
        fetch_from = start_date
    elif last_date < today:
        fetch_from = last_date
    else:
        fetch_from = today

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
