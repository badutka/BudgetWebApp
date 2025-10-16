import pandas as pd
import numpy as np

from django.db.models import F
from django_pandas.io import read_frame

from core.dashboard import data_handling, filters as data_filters
from core.constants import FMT_MAP, FREQ_MAP, KPI_COLS
from budget import models
from core.logger import logger


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


def get_date_range(date_for, freq):
    """
    Returns a formatted date range string for a given date and freq.
    Works for 'day', 'month', 'year', or any pandas frequency like 'D', 'M', 'Y', 'W', etc.
    """
    freq = FREQ_MAP.get(freq.lower(), freq.upper())  # allow 'M', 'Y', etc.
    period = pd.to_datetime(date_for).to_period(freq)

    start = period.start_time.date()
    end = period.end_time.date()

    return f"{start}" if start == end else f"{start} → {end}"


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


def update_kpi_data():
    """

    :return:
    """
    # Step 1: Query with select_related to avoid extra DB hits
    # qs = models.Transaction.objects.select_related('category').all()
    qs = models.Transaction.objects.select_related('category').annotate(category_name=F('category__name'))

    # Step 2: Convert to DataFrame
    df = read_frame(qs, fieldnames=['id', 'date', 'amount', 'category_name', 'category__transaction_type',
                                    'category__parent_category'])

    # Rename for clarity
    df.rename(columns={'category__transaction_type': 'transaction_type', 'category__parent_category': 'parent_category',
                       'category_name': 'category'}, inplace=True)

    # Step 3: Ensure datetime
    df['date'] = pd.to_datetime(df['date'])

    # Add groupable time units
    df['day'] = df['date'].dt.date
    df['month'] = df['date'].dt.to_period('M')
    df['year'] = df['date'].dt.to_period('Y')
    df['amount'] = df['amount'].astype(float)

    # Step 4: Pivot transaction_type to columns
    pivoted = df.pivot_table(
        index=['day', 'month', 'year', 'category', 'parent_category'],
        columns='transaction_type',
        values='amount',
        aggfunc='sum',
        fill_value=0
    ).reset_index().rename(columns={'INCOMING': 'income', 'OUTGOING': 'expenses', 'INNER': 'inner'})

    type_map = df.groupby('category')['transaction_type'].first().to_dict()
    pivoted['transaction_type'] = pivoted['category'].map(type_map)

    pivoted['net_savings'] = data_handling.get_net_savings(pivoted)
    pivoted.to_csv('../artifacts/data/dsb_kpi_data.csv', index=False)


def get_kpis(date_unit='month', date_for=None, date_from=None, date_to=None, apply_date_filters=False,
             apply_filters=False, transaction_types=None, parent_categories=None, categories=None):
    df = pd.read_csv('../artifacts/data/dsb_kpi_data.csv')

    date_unit = date_unit.lower() if date_unit and date_unit.lower() in FREQ_MAP else None
    freq = FREQ_MAP.get(date_unit)

    df_filter = data_filters.DataFilter()

    if apply_filters:
        (df_filter.by_transaction_types(transaction_types)
         .by_parent_categories(parent_categories)
         .by_categories(categories))

    if apply_date_filters:
        df_filter.by_date_range(date_from, date_to)

    df = df_filter.apply(df)

    df_agg = data_handling.group_kpis(df, group_by_col=date_unit, include_num_transactions=True)

    if date_unit:
        df_agg = data_handling.zero_fill_missing_ds(
            df_agg,
            ['income', 'expenses', 'inner', 'net_savings', 'num_transactions'],
            date_unit=date_unit,
            fill_to_start_of_year=True,
            fill_to_end_of_year=False,
            date_from=date_from,
            date_to=date_to,
            date_col=date_unit
        )

    df_agg['accounts_balance'] = data_handling.get_accounts_balance(df_agg)
    # df_agg = data_handling.fill_missing_acc_balance(df_agg)

    add_change_metrics(df_agg, KPI_COLS)

    # logger.info(f'\n{df_agg}')

    if date_unit:
        df_agg[date_unit] = pd.to_datetime(df_agg[date_unit])
        df_agg_row = df_agg[df_agg[date_unit].dt.to_period(freq) == pd.to_datetime(date_for).to_period(freq)]
        date_range = get_comparison_date_range(date_for, date_unit)
    else:
        df_agg_row = df_agg
        start_date = pd.to_datetime(df['day']).min().strftime('%d.%m.%Y')
        end_date = pd.to_datetime(df['day']).max().strftime('%d.%m.%Y')
        date_range = f'{start_date} → {end_date}'

    df_agg_row = df_agg_row.iloc[0] if not df_agg_row.empty else None
    kpis = build_kpi_result(df_agg_row, KPI_COLS, prefix='')

    # logger.info(f'\n{pd.DataFrame.from_dict(kpis)}')

    return kpis, date_range
