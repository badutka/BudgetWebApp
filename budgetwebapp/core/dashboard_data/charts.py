import os
import pandas as pd

from django.db.models import Sum

from budget import models
from core.logger import logger


def group_kpis(df, group_by_col=None):
    # Define all possible aggregations
    agg_map = {
        'INCOMING': 'sum',
        'OUTGOING': 'sum',
        'INNER': 'sum',
        'NUM_TRANSACTIONS': 'sum',
        'BALANCE': 'sum',
    }

    # Keep only the aggregations for columns that actually exist in df
    valid_agg_map = {col: agg for col, agg in agg_map.items() if col in df.columns}

    if not valid_agg_map:
        raise ValueError("None of the expected KPI columns are present in the DataFrame.")

    if group_by_col is None:
        # Single-row DataFrame with total sums
        grouped_df = df.agg(valid_agg_map).to_frame().T
    else:
        grouped_df = df.groupby(group_by_col).agg(valid_agg_map).reset_index()

    # grouped = df_kpis.groupby(group_by_col).agg({col: 'sum' for col in cols}).reset_index()

    return grouped_df.round(2)


def get_starting_balance():
    starting_balance = float(
        models.MoneyAccount.objects.aggregate(
            total=Sum('starting_balance')
        )['total'] or 0
    )
    return starting_balance


def get_accounts_balance(df, starting_balance=None):
    if not starting_balance:
        starting_balance = get_starting_balance()
    accounts_balance = round(starting_balance + (df['income'] - df['expenses']).cumsum(), 2)
    return accounts_balance


def zero_fill_missing_ds(
        df,
        cols,
        date_unit="month",  # 'day', 'month', or 'year'
        fill_to_start_of_year=False,
        fill_to_end_of_year=False
):
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.set_index("ds")

    start = df.index.min()
    end = df.index.max()

    if fill_to_start_of_year:
        start = pd.Timestamp(year=start.year, month=1, day=1)
    if fill_to_end_of_year:
        if date_unit == "year":
            end = pd.Timestamp(year=end.year, month=12, day=31)
        elif date_unit == "month":
            end = pd.Timestamp(year=end.year, month=12, day=1)
        elif date_unit == "day":
            end = pd.Timestamp(year=end.year, month=12, day=31)

    # Map date_unit to pandas freq
    freq_map = {
        "day": "D",
        "month": "MS",  # month start
        "year": "YS"  # year start
    }

    if date_unit not in freq_map:
        raise ValueError("date_unit must be 'day', 'month', or 'year'")

    full_range = pd.date_range(start, end, freq=freq_map[date_unit])

    df = df.reindex(full_range)

    for col in cols:
        df[col] = df[col].fillna(0)

    df = df.reset_index().rename(columns={"index": "ds"})
    df["ds"] = df["ds"].dt.strftime("%Y-%m-%d")

    return df


def fill_missing_acc_balance(df, col="accounts_balance"):
    # Ensure numeric (in case it's stringy), then forward-fill internal gaps
    # and backfill the leading edge.
    s = pd.to_numeric(df[col], errors="coerce")
    if s.notna().any():  # guard in case the whole column is NaN
        df[col] = s.ffill().bfill()
    else:
        df[col] = s
    return df


def calculate_chart_data():
    group_by_col = 'month'
    df = pd.read_csv('../artifacts/data/kpis_detailed.csv')
    df = group_kpis(df, group_by_col=group_by_col)

    df = df.rename(columns={
        'INCOMING': 'income',
        'OUTGOING': 'expenses',
        'BALANCE': 'net_savings',
        group_by_col: 'ds'
    })
    df = df[['ds', 'income', 'expenses', 'net_savings']]
    df['accounts_balance'] = get_accounts_balance(df)
    df = zero_fill_missing_ds(
        df,
        ['income', 'expenses', 'net_savings'],
        date_unit=group_by_col,
        fill_to_start_of_year=True,
        fill_to_end_of_year=False
    )
    df = fill_missing_acc_balance(df)

    # Savings rate
    df['savings_rate'] = round(df['net_savings'] / df['income'] * 100, 2)

    # --- NEW METRICS ---

    # 1. Cumulative expenses & income
    df['cumulative_income'] = df['income'].cumsum()
    df['cumulative_expenses'] = df['expenses'].cumsum()

    # 2. Volatility (Rolling 3-month Std Dev + Mean)
    window = 3
    df['income_mean'] = df['income'].rolling(window).mean()
    df['income_volatility'] = df['income'].rolling(window).std()
    df['expenses_mean'] = df['expenses'].rolling(window).mean()
    df['expenses_volatility'] = df['expenses'].rolling(window).std()

    # Variability bands (mean ± std)
    df['income_upper_band'] = df['income_mean'] + df['income_volatility']
    df['income_lower_band'] = df['income_mean'] - df['income_volatility']
    df['expenses_upper_band'] = df['expenses_mean'] + df['expenses_volatility']
    df['expenses_lower_band'] = df['expenses_mean'] - df['expenses_volatility']

    # Clean NaNs/infs
    df = df.replace([float('inf'), float('-inf')], 0)
    df = df.where(pd.notnull(df), 0)

    logger.debug(f'\n{df}')
    # logger.debug(df.to_dict(orient="records"))
    return df.to_dict(orient="list")

# def calculate_chart_data(summaries):
#     group_by_col = 'month'
#     df = pd.read_csv('../artifacts/data/kpis_detailed.csv')
#     df = group_kpis(df, group_by_col=group_by_col)
#
#     df = df.rename(columns={'INCOMING': 'income', 'OUTGOING': 'expenses', 'BALANCE': 'net_savings', group_by_col: 'ds'})
#     df = df[['ds', 'income', 'expenses', 'net_savings']]
#     df['accounts_balance'] = get_accounts_balance(df)
#     df = zero_fill_missing_ds(df, ['income', 'expenses', 'net_savings'], fill_to_start_of_year=True, fill_to_end_of_year=True)
#     df = fill_missing_acc_balance(df)
#
#     df['savings_rate'] = round(df['net_savings'] / df['income'] * 100, 2)
#
#
#     df = df.replace([float('inf'), float('-inf')], 0)
#     df = df.where(pd.notnull(df), 0)
#
#     logger.debug(df)
#
#     return df.to_dict(orient="list")
