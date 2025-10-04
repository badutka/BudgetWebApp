import pandas as pd
import numpy as np


class DataFilter:
    def __init__(self):
        self._filters = {}  # store filters by name

    def by_categories(self, categories):
        if categories is not None:
            self._filters['categories'] = lambda df: df['category'].isin(categories)
        return self

    def by_parent_categories(self, parent_categories):
        if parent_categories is not None:
            self._filters['parent_categories'] = lambda df: df['parent_category'].isin(parent_categories)
        return self

    def by_transaction_types(self, transaction_types):
        if transaction_types is not None:
            self._filters['transaction_types'] = lambda df: df['transaction_type'].isin(transaction_types)
        return self

    def by_date_range(self, date_from=None, date_to=None, date_col='day'):
        if date_from is not None or date_to is not None:
            def _date_filter(df):
                if not np.issubdtype(df[date_col].dtype, np.datetime64):
                    df = df.copy()
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

                mask = pd.Series(True, index=df.index)
                if date_from is not None:
                    mask &= df[date_col] >= pd.to_datetime(date_from)
                if date_to is not None:
                    mask &= df[date_col] <= pd.to_datetime(date_to)
                return mask

            self._filters['date_range'] = _date_filter
        return self

    def apply(self, df: pd.DataFrame, filter_name: str = None) -> pd.DataFrame:
        """
        Apply all filters if filter_name is None.
        Apply only the named filter if filter_name is provided.
        """
        if not self._filters:
            return df

        if filter_name:
            f = self._filters.get(filter_name)
            if f is None:
                raise ValueError(f"No filter found with name '{filter_name}'")
            mask = f(df)
        else:
            mask = pd.Series(True, index=df.index)
            for f in self._filters.values():
                mask &= f(df)

        return df[mask]
