import pandas as pd

from django.db.models import F
from django_pandas.io import read_frame

from budget import models
from core.dashboard import data_handling, filters as data_filters
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


def update_summary_data():
    qs = models.Transaction.objects.select_related('category').annotate(category_name=F('category__name'))
    df = read_frame(qs, fieldnames=['id', 'date', 'amount', 'category_name', 'category__transaction_type',
                                    'category__parent_category'])
    df.rename(columns={'category__transaction_type': 'transaction_type', 'category__parent_category': 'parent_category',
                       'category_name': 'category'}, inplace=True)

    df['day'] = pd.to_datetime(df['date'])
    df['month'] = df['day'].dt.to_period('M')
    df['year'] = df['day'].dt.to_period('Y')
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

    pivoted['net_savings'] = data_handling.get_net_savings(pivoted)

    pivoted.to_csv('../artifacts/data/dsb_summary_data.csv', index=False)


def get_summaries(date_unit='month', date_for=None, date_from=None, date_to=None, apply_date_filters=False,
             apply_filters=False, transaction_types=None, parent_categories=None, categories=None):
    date_unit = 'month'
    df = pd.read_csv('../artifacts/data/dsb_summary_data.csv')

    df_filter = data_filters.DataFilter()

    if apply_filters:
        df_filter = (
            df_filter
            .by_transaction_types(transaction_types)
            .by_parent_categories(parent_categories)
            .by_categories(categories)
        )

    if apply_date_filters:
        df_filter = df_filter.by_date_range(date_from, date_to)

    df = df_filter.apply(df)

    df = data_handling.group_kpis(df, group_by_col=date_unit)

    df = df.rename(columns={date_unit: 'ds'})

    df = data_handling.zero_fill_missing_ds(
        df,
        ['income', 'expenses', 'net_savings'],
        date_unit=date_unit,
        fill_to_start_of_year=True,
        fill_to_end_of_year=False,
        date_from=date_from,
        date_to=date_to
    )

    df['accounts_balance'] = data_handling.get_accounts_balance(df)
    # df = data_handling.fill_missing_acc_balance(df)
    df = data_handling.calculate_savings_rate(df)
    df = data_handling.accumulate_fields(df, ['income', 'expenses'])
    df = calculate_volatility(df)

    # Clean NaNs/infs
    df = df.replace([float('inf'), float('-inf')], 0)
    df = df.where(pd.notnull(df), 0)

    # logger.debug(f'\n{df}')

    # logger.debug(df.to_dict(orient="records"))
    return df.to_dict(orient="list")
