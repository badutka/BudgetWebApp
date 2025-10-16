import pandas as pd
from datetime import datetime
import numpy as np

from django.db.models import Sum

from budget import models
from core.constants import FMT_MAP, FREQ_MAP, KPI_COLS
from core.logger import logger


def calculate_volatility(df, window=3):
    # Volatility (Rolling <#window>-month Std Dev + Mean)
    df['income_mean'] = df['income'].rolling(window).mean()
    df['income_volatility'] = df['income'].rolling(window).std()
    df['expenses_mean'] = df['expenses'].rolling(window).mean()
    df['expenses_volatility'] = df['expenses'].rolling(window).std()

    # Variability bands (mean ± std)
    df['income_upper_band'] = df['income_mean'] + df['income_volatility']
    df['income_lower_band'] = df['income_mean'] - df['income_volatility']
    df['expenses_upper_band'] = df['expenses_mean'] + df['expenses_volatility']
    df['expenses_lower_band'] = df['expenses_mean'] - df['expenses_volatility']

    return df


def add_change_metrics(df, columns, suffix='', as_string=False):
    """
    Adds nominal (raw) and percentage change columns to a DataFrame for given numeric columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing numeric columns.
    columns : list of str
        Column names for which to calculate changes.
    suffix : str, optional
        Optional suffix for new column names (e.g., 'mtd' or 'yoy').
        The resulting columns will be named as: <col>_<suffix>_chg and <col>_<suffix>_pct.
    as_string : bool, optional
        If True, percentage values are formatted as strings (e.g., "12.5%").
        Default is False (numeric values are retained).

    Notes
    -----
    - Nominal (raw) change is calculated as the simple difference between
      the current and previous row using `df[col].diff()`.
    - Percentage change is calculated relative to the absolute value of the previous observation:
          pct = (current - previous) / abs(previous)
      Using `abs(previous)` ensures that when values cross zero or both
      are negative (e.g., going from -10000 → -5000), the direction of
      change still reflects *improvement* (+50%) rather than a misleading
      negative (-50%) that would arise from dividing by a negative base.
    - Infinite and NaN values are replaced with "N/A" for readability.

    Returns
    -------
    pd.DataFrame
        The same DataFrame with added `__chg` and `__pct` columns.
    """

    for col in columns:
        pct_col = f"{col.lower()}_{suffix}_pct"
        nom_col = f"{col.lower()}_{suffix}_chg"

        # Nominal (raw) change
        # The diff() result is a Series of np.float64,
        # but calling fillna("N/A") mixes string with floats,
        # so Pandas upcasts the column to object dtype.
        df[nom_col] = round(df[col].diff(), 2).fillna("N/A")

        # Percentage change relative to the absolute previous value
        # Using abs() ensures directionality makes intuitive sense across zero or negative values.
        pct = (df[col].diff() / df[col].shift(1).abs()).round(4).replace([np.inf, -np.inf, np.nan], "N/A")
        # pct = round(df[col].pct_change(fill_method=None), 4).replace([np.inf, -np.inf, np.nan], "N/A")

        if as_string:
            pct = pct.apply(lambda x: f"{round(x * 100, 2)}%" if isinstance(x, (int, float, np.floating)) else "N/A")

        df[pct_col] = pct


def build_kpi_result(row, kpi_keys, prefix=None):
    result = {}

    if row is None:
        for key in kpi_keys:
            result[key] = {
                'amount': 0,
                'change': 0,
                'pct_change': "N/A"
            }
        return result

    for key in kpi_keys:
        amt_col = key
        chg_col = f"{key.lower()}_{prefix}_chg"
        pct_col = f"{key.lower()}_{prefix}_pct"
        result[key] = {
            'amount': row.get(amt_col, 0) if pd.notna(row.get(amt_col)) else 0,
            'change': row.get(chg_col, 0) if chg_col and pd.notna(row.get(chg_col)) else 0,
            'pct_change': row.get(pct_col, "N/A") if pct_col and pd.notna(row.get(pct_col)) else "N/A"
        }

    return result


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


def get_comparison_date_range(date_for, freq):
    """
    Returns a compact comparison date range string based on frequency.
    Example:
      freq='M' or 'month' → '08.2025 - 09.2025'
      freq='D' or 'day'   → '05.10.2025 - 06.10.2025'
      freq='Y' or 'year'  → '2024 - 2025'
    """
    freq = FREQ_MAP.get(freq.lower(), freq.upper())

    date_for = pd.to_datetime(date_for)
    period = date_for.to_period(freq)
    prev_period = period - 1

    fmt = FMT_MAP.get(freq, "%Y-%m-%d")

    prev_str = prev_period.start_time.strftime(fmt)
    curr_str = period.start_time.strftime(fmt)

    return f"{prev_str} → {curr_str}"


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
