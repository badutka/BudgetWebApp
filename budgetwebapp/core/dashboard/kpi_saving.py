import pandas as pd
import numpy as np
from django.db.models import Sum

from django_pandas.io import read_frame

from budget import models
from . import kpi_calc


def prepare_kpis(kpis, starting_balance=None):
    if 'daily' in kpis and 'day' in kpis['daily'].columns:
        daily_df = kpis['daily'].copy()
        # daily_df['day'] = pd.to_datetime(daily_df['day'])

        # Create a continuous date range
        full_range = pd.date_range(daily_df['day'].min(), daily_df['day'].max(), freq='D')
        daily_df = daily_df.set_index('day').reindex(full_range).rename_axis('day').reset_index()

        # Fill missing KPI metrics with 0
        for col in ['INCOMING', 'OUTGOING', 'INNER', 'BALANCE', 'NUM_TRANSACTIONS']:
            if col in daily_df.columns:
                daily_df[col] = daily_df[col].fillna(0.0)

        # BALANCE_REAL: carry forward last value
        if 'BALANCE_REAL' in daily_df.columns:
            # 1) Set only the first row if NaN
            if starting_balance is not None and pd.isna(daily_df['BALANCE_REAL'].iloc[0]):
                daily_df.loc[0, 'BALANCE_REAL'] = starting_balance

            # 2) Forward fill everything else
            daily_df['BALANCE_REAL'] = daily_df['BALANCE_REAL'].ffill()

        kpis['daily'] = daily_df

    return kpis


def extract_balance_kpis(df, time_col):
    kpis = (
        df.sort_values('date')
        .groupby(time_col)
        .last()
        .reset_index()[[time_col, 'balance_after']]
        .rename(columns={'balance_after': 'BALANCE_REAL'})
    )
    return kpis


def calculate_balance():
    accounts = models.MoneyAccount.objects.all()
    transactions = models.Transaction.objects.filter().reverse()
    balance = 0
    for account in accounts:
        balance += float(account.starting_balance)

    balance_history = []

    for transaction in transactions:
        old_balance = balance
        if transaction.origin and transaction.destination:
            amount = 0  # ignoring inner for now; handle inner when filtering by account.
        elif transaction.origin:
            amount = -transaction.amount
        elif transaction.destination:
            amount = transaction.amount
        else:
            amount = 0

        balance += float(amount)
        balance_history.append(
            {'date': transaction.date,
             'origin': transaction.origin,
             'destination': transaction.destination,
             'balance_before': round(old_balance, 2),
             'balance_after': round(balance, 2),
             'amount': round(amount, 2),
             'transaction_type': transaction.transaction_type,
             }
        )

    df = pd.DataFrame(balance_history)
    df['date'] = pd.to_datetime(df['date'])
    df['day'] = df['date'].dt.date
    df['month'] = df['date'].dt.to_period('M')
    df['year'] = df['date'].dt.to_period('Y')

    return df





def calculate_daily_kpis():
    """
    IDEA:
    DoD - daily change, but monthly total
    MoM - monthly change, yearly total
    YoY - yearly change, all time total
    accounts, incoming, outgoing, inner, balance

    filters: todo
    updates: for a specific column
    :return:
    """
    # Step 1: Query with select_related to avoid extra DB hits
    qs = models.Transaction.objects.select_related('category').all()

    # Step 2: Convert to DataFrame
    df = read_frame(qs, fieldnames=['id', 'date', 'amount', 'category', 'category__transaction_type',
                                    'category__parent_category'])

    # Rename for clarity
    df.rename(
        columns={'category__transaction_type': 'transaction_type', 'category__parent_category': 'parent_category'},
        inplace=True)

    # Step 3: Ensure datetime
    df['date'] = pd.to_datetime(df['date'])

    # Add groupable time units
    df['day'] = df['date'].dt.date
    df['month'] = df['date'].dt.to_period('M')
    df['year'] = df['date'].dt.to_period('Y')
    df['amount'] = df['amount'].astype(float)

    # Step 4: Pivot transaction_type to columns
    pivoted = df.pivot_table(
        index=['day', 'month', 'year'],
        columns='transaction_type',
        values='amount',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Count transactions per day
    count_df = df.groupby(['day', 'month', 'year']).size().reset_index(name='NUM_TRANSACTIONS')
    pivoted = pd.merge(pivoted, count_df, on=['day', 'month', 'year'], how='left')

    # Optional: rename columns if needed
    pivoted.columns.name = None  # remove category name from columns

    # Step 5: Group by each level
    cols = ['INCOMING', 'OUTGOING', 'INNER', 'NUM_TRANSACTIONS']
    daily_kpis = pivoted.groupby('day')[cols].sum().reset_index().round(2)
    monthly_kpis = pivoted.groupby('month')[cols].sum().reset_index().round(2)
    yearly_kpis = pivoted.groupby('year')[cols].sum().reset_index().round(2)
    all_time_kpis = pivoted[cols].sum().round(2).to_frame().T
    all_time_kpis['NUM_TRANSACTIONS'] = all_time_kpis['NUM_TRANSACTIONS'].astype(int)

    # Add balance = INCOMING - OUTGOING
    daily_kpis['BALANCE'] = round(daily_kpis['INCOMING'] - daily_kpis['OUTGOING'], 2)
    monthly_kpis['BALANCE'] = round(monthly_kpis['INCOMING'] - monthly_kpis['OUTGOING'], 2)
    yearly_kpis['BALANCE'] = round(yearly_kpis['INCOMING'] - yearly_kpis['OUTGOING'], 2)
    all_time_kpis['BALANCE'] = round(all_time_kpis['INCOMING'] - all_time_kpis['OUTGOING'], 2)

    # CUMULATIVE ACCOUNTS BALANCE = starting_balance + (INCOMING - OUTGOING)
    starting_balance = kpi_calc.get_starting_balance()
    daily_kpis['BALANCE_REAL'] = round(starting_balance + (daily_kpis['INCOMING'] - daily_kpis['OUTGOING']).cumsum(), 2)
    monthly_kpis['BALANCE_REAL'] = round(starting_balance + (monthly_kpis['INCOMING'] - monthly_kpis['OUTGOING']).cumsum(), 2)
    yearly_kpis['BALANCE_REAL'] = round(starting_balance + (yearly_kpis['INCOMING'] - yearly_kpis['OUTGOING']).cumsum(), 2)
    all_time_kpis['BALANCE_REAL'] = round(starting_balance + (all_time_kpis['INCOMING'] - all_time_kpis['OUTGOING']).cumsum(), 2)

    kpis = {
        'daily': daily_kpis,
        'monthly': monthly_kpis,
        'yearly': yearly_kpis,
        'totals': all_time_kpis
    }

    kpis = prepare_kpis(kpis)

    kpi_cols = ['INCOMING', 'OUTGOING', 'INNER', 'BALANCE', 'NUM_TRANSACTIONS', 'BALANCE_REAL']
    kpi_calc.add_change_metrics(kpis['daily'], kpi_cols, 'dod')  # Day-over-day
    kpi_calc.add_change_metrics(kpis['monthly'], kpi_cols, 'mom')  # Month-over-month
    kpi_calc.add_change_metrics(kpis['yearly'], kpi_cols, 'yoy')  # Year-over-year

    # Convert Period to timestamp for monthly and yearly
    kpis['daily']['day'] = pd.to_datetime(kpis['daily']['day'])
    kpis['monthly']['month'] = kpis['monthly']['month'].dt.to_timestamp()
    kpis['yearly']['year'] = kpis['yearly']['year'].dt.to_timestamp()

    kpis['daily'].to_csv('../artifacts/data/daily_kpis.csv', index=False)
    kpis['monthly'].to_csv('../artifacts/data/monthly_kpis.csv', index=False)
    kpis['yearly'].to_csv('../artifacts/data/yearly_kpis.csv', index=False)
    kpis['totals'].to_csv('../artifacts/data/totals_kpis.csv', index=False)

    # --- NEW: DETAILED KPI FILES ---
    # Keep breakdown by category, but also store transaction_type for filtering
    cols_with_balance = ['INCOMING', 'OUTGOING', 'INNER', 'NUM_TRANSACTIONS']

    # Pivot at transaction_type level (needed for INCOMING, OUTGOING, INNER columns)
    df_detailed = df.pivot_table(
        index=['day', 'month', 'year', 'category', 'parent_category'],
        columns='transaction_type',
        values='amount',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Add NUM_TRANSACTIONS
    counts_detailed = df.groupby(
        ['day', 'month', 'year', 'category', 'parent_category']
    ).size().reset_index(name='NUM_TRANSACTIONS')

    df_detailed = pd.merge(
        df_detailed, counts_detailed,
        on=['day', 'month', 'year', 'category', 'parent_category'],
        how='left'
    )

    df_detailed.columns.name = None
    df_detailed['BALANCE'] = round(df_detailed['INCOMING'] - df_detailed['OUTGOING'], 2)

    # Attach transaction_type (first value in group for each category)
    type_map = df.groupby('category')['transaction_type'].first().to_dict()
    df_detailed['transaction_type'] = df_detailed['category'].map(type_map)

    # Save daily/monthly/yearly breakdowns
    daily_detail = df_detailed.groupby(['day', 'category', 'parent_category']).agg({
        **{col: 'sum' for col in cols_with_balance + ['BALANCE']},
        'transaction_type': 'first'
    }).reset_index().round(2)

    monthly_detail = df_detailed.groupby(['month', 'category', 'parent_category']).agg({
        **{col: 'sum' for col in cols_with_balance + ['BALANCE']},
        'transaction_type': 'first'
    }).reset_index().round(2)

    yearly_detail = df_detailed.groupby(['year', 'category', 'parent_category']).agg({
        **{col: 'sum' for col in cols_with_balance + ['BALANCE']},
        'transaction_type': 'first'
    }).reset_index().round(2)

    # --- Totals detailed ---
    totals_detail = df_detailed.groupby(['category', 'parent_category']).agg({
        **{col: 'sum' for col in cols_with_balance + ['BALANCE']},
        'transaction_type': 'first'
    }).reset_index().round(2)

    daily_detail['day'] = pd.to_datetime(daily_detail['day'])
    monthly_detail['month'] = monthly_detail['month'].dt.to_timestamp()
    yearly_detail['year'] = yearly_detail['year'].dt.to_timestamp()

    df_detailed['day'] = pd.to_datetime(df_detailed['day'])
    df_detailed['month'] = df_detailed['month'].dt.to_timestamp()
    df_detailed['year'] = df_detailed['year'].dt.to_timestamp()

    df_detailed.to_csv('../artifacts/data/kpis_detailed.csv', index=False)

    daily_detail.to_csv('../artifacts/data/daily_kpis_detailed.csv', index=False)
    monthly_detail.to_csv('../artifacts/data/monthly_kpis_detailed.csv', index=False)
    yearly_detail.to_csv('../artifacts/data/yearly_kpis_detailed.csv', index=False)
    totals_detail.to_csv('../artifacts/data/totals_kpis_detailed.csv', index=False)


