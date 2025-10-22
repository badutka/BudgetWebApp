from collections import defaultdict
import pandas as pd


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
