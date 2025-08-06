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
        for col in ['INCOMING', 'OUTGOING', 'INNER']:
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
        pct = round(df[col].pct_change(), 4).replace([np.inf, -np.inf, np.nan], "N/A")

        if as_string:
            pct = pct.apply(
                lambda x: f"{round(x * 100, 2)}%" if isinstance(x, (int, float, np.floating)) else "N/A"
            )

        df[pct_col] = pct


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

    # Optional: rename columns if needed
    pivoted.columns.name = None  # remove category name from columns

    # Step 5: Group by each level
    daily_kpis = pivoted.groupby('day')[['INCOMING', 'OUTGOING', 'INNER']].sum().reset_index().round(2)
    monthly_kpis = pivoted.groupby('month')[['INCOMING', 'OUTGOING', 'INNER']].sum().reset_index().round(2)
    yearly_kpis = pivoted.groupby('year')[['INCOMING', 'OUTGOING', 'INNER']].sum().reset_index().round(2)
    all_time_kpis = pivoted[['INCOMING', 'OUTGOING', 'INNER']].sum().round(2).to_frame().T

    kpis = {
        'daily': daily_kpis,
        'monthly': monthly_kpis,
        'yearly': yearly_kpis,
        'totals': all_time_kpis
    }

    # Fix missing days (fill with 0.0 where needed)
    kpis = prepare_kpis(kpis)

    # Recalculate changes AFTER filling gaps
    kpi_cols = ['INCOMING', 'OUTGOING', 'INNER']
    add_change_metrics(kpis['daily'], kpi_cols, 'dod')  # Day-over-day
    add_change_metrics(kpis['monthly'], kpi_cols, 'mom')  # Month-over-month
    add_change_metrics(kpis['yearly'], kpi_cols, 'yoy')  # Year-over-year

    # Convert Period to timestamp for monthly and yearly
    kpis['daily']['day'] = pd.to_datetime(kpis['daily']['day'])
    kpis['monthly']['month'] = kpis['monthly']['month'].dt.to_timestamp()
    kpis['yearly']['year'] = kpis['yearly']['year'].dt.to_timestamp()

    kpis['daily'].to_csv('daily_kpis.csv', index=False)
    kpis['monthly'].to_csv('monthly_kpis.csv', index=False)
    kpis['yearly'].to_csv('yearly_kpis.csv', index=False)
    kpis['totals'].to_csv('totals_kpis.csv', index=False)