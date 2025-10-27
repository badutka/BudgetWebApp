from collections import defaultdict
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

from core.datastore import DataStore
from core.logger import logger
import time


def ENTRY_POINT():
    ticker_mapping = {
        "VUAA.L": "VUAA.UK",
        "CNDX.L": "CNDX.UK",
        "IGLN.L": "IGLN.UK",
        "IUIT.L": "IUIT.UK",
        "SPYL.DE": "SPYL.DE",
        "USDPLN=X": "USDPLN",
        "EURPLN=X": "EURPLN",
    }

    tickers = list(ticker_mapping.keys())

    fetch_market_data(tickers, ticker_mapping)


def fetch_market_data(
        tickers: list[str],
        ticker_mapping: dict[str, str],
        period: str = "1h",
        start_date: str = "2024-07-22",
        end_date: str = None,
        file_path: Path = Path("../artifacts/market_data"),
):
    file_dir = Path(file_path)
    file_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"market_prices_{period}"


    # === Load existing data ===
    try:
        df_prices = DataStore(file_path).load(file_name, fmt='parquet', prefix='')
        # df_prices = DataStore(file_path).load(file_name, fmt='csv', prefix='', parse_dates=["Date"], index_col="Date")
        # df_prices = pd.read_csv(file, parse_dates=["Date"], index_col="Date")
    except FileNotFoundError:
        df_prices = pd.DataFrame()

    # === Determine fetch start date ===
    today = datetime.now().date()
    last_date = df_prices.index[-1].date() if not df_prices.empty else None

    # Adjust for early morning (before 10 AM)
    # todo: test 00:00 AM and 09:00 AM
    if 0 <= datetime.now().hour < 10 and last_date:
        last_date -= timedelta(days=1)

    # # This has no effect
    # if 0 <= datetime.now().hour < 2 and last_date:
    #     end_date = today + timedelta(days=1)

    if last_date is None:
        fetch_from = start_date
    elif last_date < today:
        fetch_from = last_date
    else:
        fetch_from = today

    # === Download new data ===
    # todo: (1h 2025-10-24 -> 2025-10-23 23:17:19+01:00) (Yahoo error = "Invalid input - start date cannot be after end date. startDate = 1761260400, endDate = 1761257839")')
    df_new = yf.download(tickers, interval=period, start=fetch_from, end=end_date, auto_adjust=True)["Close"]
    df_new.columns.name = None  # since 26.10.2025 ticker columns seem to be named "Ticker"

    if period in ("1h", "30m"):
        df_new.index.name = "Date"
        df_new.index = (df_new.index.tz_convert("Europe/Warsaw").tz_localize(None))

    df_new.rename(columns=ticker_mapping, inplace=True)
    df_new = df_new.ffill().bfill()

    # === Combine old + new ===
    if not df_new.empty:
        logger.info(f"New data downloaded: {df_new.index[0]} - {df_new.index[-1]} ({tickers}).")
        df_prices = pd.concat([df_prices, df_new]).pipe(
            lambda df: df.loc[~df.index.duplicated(keep="last")].sort_index()
        )
    else:
        logger.info("No new data to download.")

    # === Save updated data ===
    DataStore(file_path).save(file_name, df_prices, fmt='parquet', index=True, prefix='')
    # DataStore(file_path).save(file_name, df_prices, fmt='csv', index=True, prefix='')
    # df_prices.to_csv(file)

    return df_prices
