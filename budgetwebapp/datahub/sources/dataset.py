# datahub/sources/dataset.py

import sqlite3
import pandas as pd

from django.conf import settings

from budgetwebapp.datahub.sources.base import BaseDataSource
from budgetwebapp.datahub.sources.registry import register_data_source
from budgetwebapp.datahub.models import Dataset


@register_data_source("dataset")
class DatasetDataSource(BaseDataSource):

    def fetch(self, query: dict, context: dict | None = None):
        dataset_name = query["dataset"]

        dataset = Dataset.objects.select_related("current_artifact").get(
            name=dataset_name
        )

        artifact = dataset.current_artifact

        if artifact is None:
            return []

        table_name = artifact.table_name

        conn = sqlite3.connect(settings.WAREHOUSE_DB_PATH)

        try:
            df = pd.read_sql(
                f"SELECT * FROM {table_name}",
                conn
            )
        finally:
            conn.close()

        return df.to_dict(orient="records")