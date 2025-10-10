import pandas as pd
from datetime import datetime

from django.db.models import Sum

from budget import models
from core.logger import logger


def group_kpis(df, group_by_col=None, include_num_transactions=False):
    # Define all possible aggregations
    agg_map = {
        'income': 'sum',
        'expenses': 'sum',
        'inner': 'sum',
        'net_savings': 'sum',
        'accounts_balance': 'sum'
    }

    # Keep only the aggregations for columns that actually exist in df
    valid_agg_map = {col: agg for col, agg in agg_map.items() if col in df.columns}

    if not valid_agg_map:
        raise ValueError("None of the expected KPI columns are present in the DataFrame.")

    if group_by_col is None:
        # Single-row DataFrame with total sums
        grouped_df = df.agg(valid_agg_map).to_frame().T
        if include_num_transactions:
            grouped_df["num_transactions"] = len(df)
    else:
        grouped_df = df.groupby(group_by_col).agg(valid_agg_map).reset_index()
        if include_num_transactions:
            grouped_df["num_transactions"] = df.groupby(group_by_col).size().values

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


def get_net_savings(df):
    net_savings = round(df['income'] - df['expenses'], 2)
    return net_savings


def zero_fill_missing_ds(
        df,
        cols,
        date_unit="month",  # 'day', 'month', or 'year'
        fill_to_start_of_year=False,
        fill_to_end_of_year=False,
        date_from=None,
        date_to=None,
        date_col="ds"
):
    # Map date_unit to pandas freq
    freq_map = {"day": "D", "month": "MS", "year": "YS"}
    if date_unit not in freq_map:
        raise ValueError("date_unit must be 'day', 'month', or 'year'")

    # Determine start and end
    if df.empty:
        current_year = datetime.now().year
        start = pd.Timestamp(year=current_year, month=1, day=1)
        end = pd.Timestamp(year=current_year, month=12, day=31)
    else:
        # Convert ds according to date_unit
        if date_unit == "year":
            df[date_col] = pd.to_datetime(df[date_col].astype(str), format="%Y")
        elif date_unit == "month":
            df[date_col] = pd.to_datetime(df[date_col].astype(str), format="%Y-%m")
        else:  # day
            df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
        start = df.index.min()
        end = df.index.max()

    # Adjust to start/end of year if requested
    if fill_to_start_of_year:
        start = pd.Timestamp(year=start.year, month=1, day=1)
    if fill_to_end_of_year:
        if date_unit == "year":
            end = pd.Timestamp(year=end.year, month=12, day=31)
        elif date_unit == "month":
            end = pd.Timestamp(year=end.year, month=12, day=1)
        elif date_unit == "day":
            end = pd.Timestamp(year=end.year, month=12, day=31)

    # Use provided date_from/date_to if available
    if date_from:
        start = max(pd.Timestamp(date_from), start)
    if date_to:
        end = min(pd.Timestamp(date_to), end)

    # Generate full date range
    full_range = pd.date_range(start, end, freq=freq_map[date_unit])

    # Create or reindex DataFrame
    if df.empty:
        df = pd.DataFrame({date_col: full_range})
        for col in cols:
            df[col] = 0
    else:
        df = df.reindex(full_range)
        for col in cols:
            df[col] = df[col].fillna(0)
        df = df.reset_index().rename(columns={"index": date_col})

    df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")

    return df


def accumulate_fields(df, fields):
    for field in fields:
        df[f'cumulative_{field}'] = df[field].cumsum()
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


def calculate_savings_rate(df):
    df['savings_rate'] = round(df['net_savings'] / df['income'] * 100, 2)
    return df
