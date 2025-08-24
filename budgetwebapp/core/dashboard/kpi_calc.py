import numpy as np
import pandas as pd

from django.db.models import Sum

from budget import models
from core.logger import logger


def add_change_metrics(df, columns, suffix, as_string=False):
    for col in columns:
        pct_col = f"{col.lower()}_{suffix}_pct"
        nom_col = f"{col.lower()}_{suffix}_chg"

        # Nominal (raw) change
        # The diff() result is a Series of np.float64,
        # but calling fillna("N/A") mixes string with floats,
        # so Pandas upcasts the column to object dtype.
        df[nom_col] = round(df[col].diff(), 2).fillna("N/A")

        pct = round(df[col].pct_change(fill_method=None), 4).replace([np.inf, -np.inf, np.nan], "N/A")

        if as_string:
            pct = pct.apply(lambda x: f"{round(x * 100, 2)}%" if isinstance(x, (int, float, np.floating)) else "N/A")

        df[pct_col] = pct


def get_starting_balance():
    starting_balance = float(
        models.MoneyAccount.objects.aggregate(
            total=Sum('starting_balance')
        )['total'] or 0
    )
    return starting_balance


def group_kpis(df, group_by_col=None):
    agg_map = {
        'INCOMING': 'sum',
        'OUTGOING': 'sum',
        'INNER': 'sum',
        'NUM_TRANSACTIONS': 'sum',
        'BALANCE': 'sum',
    }

    if group_by_col is None:
        # Single-row DataFrame with total sums
        grouped_df = df.agg(agg_map).to_frame().T
    else:
        grouped_df = df.groupby(group_by_col).agg(agg_map).reset_index()

    # grouped = df_kpis.groupby(group_by_col).agg({col: 'sum' for col in cols}).reset_index()

    grouped_df = grouped_df.round(2)
    return grouped_df


def filter_by_deprecated(df, transaction_types=None, categories=None, parent_categories=None):
    if categories:
        df = df[df['category'].isin(categories)]
    if parent_categories:
        df = df[df['parent_category'].isin(parent_categories)]
    if transaction_types:
        df = df[df['transaction_type'].isin(transaction_types)]

    return df

def filter_by(df, transaction_types=None, categories=None, parent_categories=None):
    if categories is not None:
        df = df[df['category'].isin(categories)]
    if parent_categories is not None:
        df = df[df['parent_category'].isin(parent_categories)]
    if transaction_types is not None:
        df = df[df['transaction_type'].isin(transaction_types)]
    return df


def calculate_accounts_balance(df, starting_balance):
    df['BALANCE_REAL'] = round(starting_balance + (df['INCOMING'] - df['OUTGOING']).cumsum(), 2)
    return df


def filter_by_date_range(df, date_from=None, date_to=None):
    """
    Filter DataFrame by 'day' column between date_from and date_to.
    'day' can be datetime, date, or string.
    date_from and date_to can be None.
    """
    # Ensure 'day' is a datetime64[ns]
    if not np.issubdtype(df['day'].dtype, np.datetime64):
        df = df.copy()
        df['day'] = pd.to_datetime(df['day'], errors='coerce')

    mask = pd.Series(True, index=df.index)

    if date_from is not None:
        mask &= df['day'] >= pd.to_datetime(date_from)

    if date_to is not None:
        mask &= df['day'] <= pd.to_datetime(date_to)

    return df[mask]


def calculate_kpis(df_kpis, group_by_col=None, transaction_types=None, categories=None, parent_categories=None, starting_balance=0, suffix='mom'):
    cols = ['INCOMING', 'OUTGOING', 'INNER', 'NUM_TRANSACTIONS', 'BALANCE', 'BALANCE_REAL']

    # 1) Filter by category / parent_category
    df_kpis = filter_by(df_kpis, transaction_types, categories, parent_categories)

    # 2) Aggregate directly by the time grouping
    grouped = group_kpis(df_kpis, group_by_col)

    # Balance is already calculated, but BALANCE_REAL has to be calculated here, because it's cumulative
    grouped = calculate_accounts_balance(grouped, starting_balance)

    add_change_metrics(grouped, cols, suffix)

    return grouped


def calculate_kpis_between_dates(df_kpis, group_by_col=None, transaction_types=None, categories=None, parent_categories=None, date_from=None,
                                 date_to=None, starting_balance=0, suffix='mom'):
    cols = ['INCOMING', 'OUTGOING', 'INNER', 'NUM_TRANSACTIONS', 'BALANCE', 'BALANCE_REAL']

    # 1) Filter by date
    df_kpis = filter_by_date_range(df_kpis, date_from=date_from, date_to=date_to)

    # 2) Filter by category / parent_category
    df_kpis = filter_by(df_kpis, transaction_types, categories, parent_categories)

    # 3) Aggregate directly by the time grouping
    grouped = group_kpis(df_kpis, group_by_col)

    grouped = calculate_accounts_balance(grouped, starting_balance)

    if suffix:
        add_change_metrics(grouped, cols, suffix)

    return grouped
