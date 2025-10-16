import pandas as pd
from django.db.models import F
from django_pandas.io import read_frame
from core.dashboard import data_handling, filters as data_filters
from core.dashboard.data_handling import calculate_volatility
from core.dashboard.datastore import DataStore
from budget import models
from core.logger import logger


class DataPipeline:
    DATA_PATH = "../artifacts/data/"
    MODEL = models.Transaction

    def __init__(self):
        self.datastore = DataStore()

    def fetch(self, extra_fields=None):
        fields = ['id', 'date', 'amount', 'category_name', 'category__transaction_type', 'category__parent_category']
        if extra_fields:
            fields += extra_fields

        qs = self.MODEL.objects.select_related('category').annotate(category_name=F('category__name'))
        df = read_frame(qs, fieldnames=fields)

        df.rename(columns={
            'category__transaction_type': 'transaction_type',
            'category__parent_category': 'parent_category',
            'category_name': 'category'
        }, inplace=True)

        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = df['amount'].astype(float)
        df['day'] = df['date'].dt.date
        df['month'] = df['date'].dt.to_period('M')
        df['year'] = df['date'].dt.to_period('Y')

        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Override this in subclasses."""
        raise NotImplementedError

    def apply_filters(self, df, date_from=None, date_to=None, apply_date=False, apply_data=False,
                      transaction_types=None, parent_categories=None, categories=None):
        df_filter = data_filters.DataFilter()
        if apply_data:
            df_filter = (
                df_filter
                .by_transaction_types(transaction_types)
                .by_parent_categories(parent_categories)
                .by_categories(categories)
            )
        if apply_date:
            df_filter = df_filter.by_date_range(date_from, date_to)
        return df_filter.apply(df)

    def save(self, name, df):
        self.datastore.save(name, df)

    def load(self, name):
        df = self.datastore.load(name)
        return df

    def run_update(self, name, extra_fields=None):
        df = self.fetch(extra_fields=extra_fields)
        df = self.transform(df)
        return self.save(name, df)


class KpiPipeline(DataPipeline):
    def transform(self, df):
        pivoted = df.pivot_table(
            index=['day', 'month', 'year', 'category', 'parent_category'],
            columns='transaction_type',
            values='amount',
            aggfunc='sum',
            fill_value=0
        ).reset_index().rename(columns={
            'INCOMING': 'income',
            'OUTGOING': 'expenses',
            'INNER': 'inner'
        })

        type_map = df.groupby('category')['transaction_type'].first().to_dict()
        pivoted['transaction_type'] = pivoted['category'].map(type_map)

        pivoted['net_savings'] = data_handling.get_net_savings(pivoted)
        return pivoted


class SummaryPipeline(DataPipeline):
    def transform(self, df):
        pivoted = df.pivot_table(
            index=['day', 'month', 'year', 'category', 'parent_category'],
            columns='transaction_type',
            values='amount',
            aggfunc='sum',
            fill_value=0
        ).reset_index().rename(columns={
            'INCOMING': 'income',
            'OUTGOING': 'expenses'
        }).drop(columns='INNER', errors='ignore')

        type_map = df.groupby('category')['transaction_type'].first().to_dict()
        pivoted['transaction_type'] = pivoted['category'].map(type_map)

        pivoted['net_savings'] = data_handling.get_net_savings(pivoted)
        pivoted = calculate_volatility(pivoted)
        return pivoted


class CategoriesPipeline(DataPipeline):
    def transform(self, df):
        grouped = df.groupby(['day', 'month', 'year', 'category']).agg(
            num_transactions=('id', 'count'),
            amount=('amount', 'sum'),
            transaction_type=('transaction_type', 'first'),
            parent_category=('parent_category', 'first')
        ).reset_index()
        return grouped


PIPELINES = {
    "kpi": KpiPipeline,
    "summary": SummaryPipeline,
    "categories": CategoriesPipeline,
}


def run_pipeline(name: str):
    pipeline_cls = PIPELINES.get(name)
    if not pipeline_cls:
        raise ValueError(f"Unknown pipeline '{name}'")
    pipeline = pipeline_cls()
    return pipeline.run_update(f"{name}_data")
