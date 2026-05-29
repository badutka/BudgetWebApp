# budgetwebapp/datahub/sources/timeseries.py

from budgetwebapp.datahub.sources.base import BaseDataSource
from budgetwebapp.datahub.sources.registry import register_data_source


@register_data_source("timeseries")
class TimeSeriesDataSource(BaseDataSource):

    def fetch(self, query: dict, context: dict | None = None):
        # account_type = query.get("account_type")

        # account_type = (query or {}).get("account_type")

        
        raw = [
            {"date": "2026-01-01", "account_type": "main", "invested": 20000, "value": 21000},
            {"date": "2026-02-01", "account_type": "main", "invested": 22000, "value": 23000},
            {"date": "2026-03-01", "account_type": "main", "invested": 24000, "value": 30000},
            {"date": "2026-04-01", "account_type": "main", "invested": 29000, "value": 45000},
            {"date": "2026-01-01", "account_type": "ike", "invested": 800, "value": 900},
            {"date": "2026-02-01", "account_type": "ike", "invested": 900, "value": 950},
            {"date": "2026-03-01", "account_type": "ike", "invested": 900, "value": 950},
            {"date": "2026-04-01", "account_type": "ike", "invested": 900, "value": 950},
        ]

        return raw
