import pandas as pd
import numpy as np

from django.db.models import F
from django_pandas.io import read_frame

from core.dashboard import data_handling, filters as data_filters
from core.constants import FMT_MAP, FREQ_MAP, KPI_COLS
from budget import models
from core.dashboard.datastore import DataStore
from core.logger import logger

datastore = DataStore()

def update_categories_data():
    qs = models.Transaction.objects.select_related('category').annotate(category_name=F('category__name'))

    # Step 2: Convert to DataFrame
    df = read_frame(qs, fieldnames=['id', 'date', 'amount', 'category_name', 'category__transaction_type',
                                    'category__parent_category'])
    df.rename(columns={'category__transaction_type': 'transaction_type', 'category__parent_category': 'parent_category',
                       'category_name': 'category'}, inplace=True)

    df = df.groupby('category').agg(
        num_transactions=('id', 'count'),
        transactions_amount=('amount', 'sum'),
        transaction_type=('transaction_type', 'first'),
        parent_category=('parent_category', 'first')
    ).reset_index()

    datastore.save("categories_data", df)


def get_categories_data():
    update_categories_data()
    df = datastore.load("categories_data")

    df_parent_categories = df.groupby(['parent_category', 'transaction_type']).agg(
        num_transactions=('num_transactions', 'sum'),
        transactions_amount=('transactions_amount', 'sum')
    ).reset_index()

    df_categories = df.groupby(['category']).agg(
        num_transactions=('num_transactions', 'sum'),
        transactions_amount=('transactions_amount', 'sum')
    ).reset_index()

    df_categories['transactions_amount'] = df_categories['transactions_amount'].astype(float)

    df_categories = df_categories.sort_values(by='num_transactions', ascending=False)
    df_parent_categories = df_parent_categories.sort_values(by='num_transactions', ascending=False)

    logger.info(df_parent_categories)
    logger.info(df_categories)

    return (df_parent_categories.to_dict(orient="list"),
            df_categories.to_dict(orient="list"))

