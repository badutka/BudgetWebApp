import pandas as pd
import numpy as np

from django.db.models import F
from django_pandas.io import read_frame

from core.dashboard import data_handling, filters as data_filters
from core.constants import FMT_MAP, FREQ_MAP, KPI_COLS
from budget import models
from core.logger import logger

def get_categories_data():
    qs = models.Transaction.objects.select_related('category').annotate(category_name=F('category__name'))

    # Step 2: Convert to DataFrame
    df = read_frame(qs, fieldnames=['id', 'date', 'amount', 'category_name', 'category__transaction_type',
                                    'category__parent_category'])
    df.rename(columns={'category__transaction_type': 'transaction_type', 'category__parent_category': 'parent_category',
                       'category_name': 'category'}, inplace=True)

    df = df.groupby('parent_category').agg(
        count=('id', 'count')
    ).reset_index()
    logger.info(df)

    return df.to_dict(orient="list")