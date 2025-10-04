import os
import pandas as pd
from datetime import datetime

from django.db.models import Sum, F
from django_pandas.io import read_frame

from budget import models
from core.dashboard_data import filters as data_filters
from core.logger import logger


def group_kpis(df, group_by_col=None):
    # Define all possible aggregations
    agg_map = {
        'INCOMING': 'sum',
        'OUTGOING': 'sum',
        'INNER': 'sum',
        'NUM_TRANSACTIONS': 'sum',
        'BALANCE': 'sum',
        'income': 'sum',
        'expenses': 'sum',
        'net_savings': 'sum',
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


def get_net_savings(df):
    df['net_savings'] = round(df['income'] - df['expenses'], 2)
    return df


def zero_fill_missing_ds(
        df,
        cols,
        date_unit="month",  # 'day', 'month', or 'year'
        fill_to_start_of_year=False,
        fill_to_end_of_year=False,
        date_from=None,
        date_to=None,
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
            df["ds"] = pd.to_datetime(df["ds"].astype(str), format="%Y")
        elif date_unit == "month":
            df["ds"] = pd.to_datetime(df["ds"].astype(str), format="%Y-%m")
        else:  # day
            df["ds"] = pd.to_datetime(df["ds"])
        df = df.set_index("ds")
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
        logger.critical(f'{start = }')
    if date_to:
        end = min(pd.Timestamp(date_to), end)

    # Generate full date range
    full_range = pd.date_range(start, end, freq=freq_map[date_unit])

    # Create or reindex DataFrame
    if df.empty:
        df = pd.DataFrame({"ds": full_range})
        for col in cols:
            df[col] = 0
    else:
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


def calculate_savings_rate(df):
    df['savings_rate'] = round(df['net_savings'] / df['income'] * 100, 2)
    return df


def accumulate_fields(df, fields):
    for field in fields:
        df[f'cumulative_{field}'] = df[field].cumsum()
    return df


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


def save_data():
    qs = models.Transaction.objects.select_related('category').annotate(category_name=F('category__name'))
    df = read_frame(qs, fieldnames=['id', 'date', 'amount', 'category_name', 'category__transaction_type',
                                    'category__parent_category'])
    df.rename(columns={'category__transaction_type': 'transaction_type', 'category__parent_category': 'parent_category',
                       'category_name': 'category'}, inplace=True)

    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M')
    df['year'] = df['date'].dt.to_period('Y')
    df.rename(columns={'date': 'day'}, inplace=True)
    df['amount'] = df['amount'].astype(float)

    pivoted = df.pivot_table(
        index=['day', 'month', 'year', 'category', 'parent_category'],
        columns='transaction_type',
        values='amount',
        aggfunc='sum',
        fill_value=0
    ).reset_index().rename(columns={'INCOMING': 'income', 'OUTGOING': 'expenses'}).drop(columns='INNER')

    pivoted.columns.name = None

    type_map = df.groupby('category')['transaction_type'].first().to_dict()
    pivoted['transaction_type'] = pivoted['category'].map(type_map)

    pivoted = get_net_savings(pivoted)

    pivoted.to_csv('../artifacts/data/dsb_summary_data.csv', index=False)


def calculate_chart_data(filters_obj: dict[str, str | list[str] | bool | None]):
    date_unit = 'month'
    save_data()
    df = pd.read_csv('../artifacts/data/dsb_summary_data.csv')
    # df = pd.read_csv('../artifacts/data/kpis_detailed.csv')
    logger.debug(f'\n{df}')

    df_filter = data_filters.DataFilter()

    if filters_obj['apply_filters']:
        df_filter = (
            df_filter
            .by_transaction_types(filters_obj['transaction_types'])
            .by_parent_categories(filters_obj['parent_categories'])
            .by_categories(filters_obj['categories'])
        )

    if filters_obj['apply_date_filters']:
        df_filter = df_filter.by_date_range(filters_obj['date_from'], filters_obj['date_to'])

    df = df_filter.apply(df)

    df = group_kpis(df, group_by_col=date_unit)

    df = df.rename(columns={date_unit: 'ds'})

    df = zero_fill_missing_ds(
        df,
        ['income', 'expenses', 'net_savings'],
        date_unit=date_unit,
        fill_to_start_of_year=True,
        fill_to_end_of_year=False,
        date_from=filters_obj['date_from'],
        date_to=filters_obj['date_to']
    )
    logger.debug(f'\n{df}')

    df['accounts_balance'] = get_accounts_balance(df)
    df = fill_missing_acc_balance(df)
    df = calculate_savings_rate(df)
    df = accumulate_fields(df, ['income', 'expenses'])
    df = calculate_volatility(df)

    # Clean NaNs/infs
    df = df.replace([float('inf'), float('-inf')], 0)
    df = df.where(pd.notnull(df), 0)

    logger.debug(f'\n{df}')

    # logger.debug(df.to_dict(orient="records"))
    return df.to_dict(orient="list")
