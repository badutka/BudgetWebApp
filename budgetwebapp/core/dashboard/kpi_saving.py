import pandas as pd
import numpy as np

from django_pandas.io import read_frame

from budget import models

def prepare_kpis(kpis):
    if 'daily' in kpis and 'day' in kpis['daily'].columns:
        daily_df = kpis['daily'].copy()
        # daily_df['day'] = pd.to_datetime(daily_df['day'])

        full_range = pd.date_range(daily_df['day'].min(), daily_df['day'].max(), freq='D')
        daily_df = daily_df.set_index('day').reindex(full_range).rename_axis('day').reset_index()

        # Fill missing INCOMING/OUTGOING/INNER with 0.0
        for col in ['INCOMING', 'OUTGOING', 'INNER', 'BALANCE', 'BALANCE_REAL']:
            if col in daily_df.columns:
                daily_df[col] = daily_df[col].fillna(0.0)

        kpis['daily'] = daily_df

    return kpis


def add_change_metrics(df, columns, suffix, as_string=False):
    for col in columns:
        pct_col = f"{col.lower()}_{suffix}_pct"
        nom_col = f"{col.lower()}_{suffix}_chg"

        # Nominal (raw) change
        # The diff() result is a Series of np.float64,
        # but calling fillna("N/A") mixes string with floats,
        # so Pandas upcasts the column to object dtype.
        df[nom_col] = round(df[col].diff(), 2).fillna("N/A")
        # df[nom_col] = df[col].diff().fillna(0.0)  # Default: 0.0 change on first row

        # Percent change (safe)
        # pct = df[col].pct_change().replace([np.inf, -np.inf], pd.NA)
        pct = round(df[col].pct_change(fill_method=None), 4).replace([np.inf, -np.inf, np.nan], "N/A")

        if as_string:
            pct = pct.apply(
                lambda x: f"{round(x * 100, 2)}%" if isinstance(x, (int, float, np.floating)) else "N/A"
            )

        df[pct_col] = pct

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
    df.rename(columns={'category__transaction_type': 'transaction_type'}, inplace=True)

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
    daily_kpis['BALANCE'] = daily_kpis['INCOMING'] - daily_kpis['OUTGOING']
    monthly_kpis['BALANCE'] = monthly_kpis['INCOMING'] - monthly_kpis['OUTGOING']
    yearly_kpis['BALANCE'] = yearly_kpis['INCOMING'] - yearly_kpis['OUTGOING']
    all_time_kpis['BALANCE'] = all_time_kpis['INCOMING'] - all_time_kpis['OUTGOING']

    balance_df = calculate_balance()
    real_daily = extract_balance_kpis(balance_df, 'day')
    real_monthly = extract_balance_kpis(balance_df, 'month')
    real_yearly = extract_balance_kpis(balance_df, 'year')
    real_total = pd.DataFrame([{'BALANCE_REAL': balance_df['balance_after'].iloc[-1]}])

    kpis = {
        'daily': daily_kpis,
        'monthly': monthly_kpis,
        'yearly': yearly_kpis,
        'totals': all_time_kpis
    }

    kpis['daily'] = pd.merge(kpis['daily'], real_daily, how='left', on='day')
    kpis['monthly'] = pd.merge(kpis['monthly'], real_monthly, how='left', on='month')
    kpis['yearly'] = pd.merge(kpis['yearly'], real_yearly, how='left', on='year')
    kpis['totals'] = pd.concat([kpis['totals'], real_total], axis=1)

    kpis = prepare_kpis(kpis)

    kpi_cols = ['INCOMING', 'OUTGOING', 'INNER', 'BALANCE', 'NUM_TRANSACTIONS', 'BALANCE_REAL']
    add_change_metrics(kpis['daily'], kpi_cols, 'dod')  # Day-over-day
    add_change_metrics(kpis['monthly'], kpi_cols, 'mom')  # Month-over-month
    add_change_metrics(kpis['yearly'], kpi_cols, 'yoy')  # Year-over-year

    # Convert Period to timestamp for monthly and yearly
    kpis['daily']['day'] = pd.to_datetime(kpis['daily']['day'])
    kpis['monthly']['month'] = kpis['monthly']['month'].dt.to_timestamp()
    kpis['yearly']['year'] = kpis['yearly']['year'].dt.to_timestamp()
    # print(kpis['totals']['NUM_TRANSACTIONS'])
    kpis['daily'].to_csv('daily_kpis.csv', index=False)
    kpis['monthly'].to_csv('monthly_kpis.csv', index=False)
    kpis['yearly'].to_csv('yearly_kpis.csv', index=False)
    kpis['totals'].to_csv('totals_kpis.csv', index=False)