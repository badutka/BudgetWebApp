import pandas as pd
import numpy as np


class DataFilter:
    def __init__(self):
        self._filters = []

    def by_categories(self, categories):
        if categories is not None:
            self._filters.append(lambda df: df['category'].isin(categories))
        return self

    def by_parent_categories(self, parent_categories):
        if parent_categories is not None:
            self._filters.append(lambda df: df['parent_category'].isin(parent_categories))
        return self

    def by_transaction_types(self, transaction_types):
        if transaction_types is not None:
            self._filters.append(lambda df: df['transaction_type'].isin(transaction_types))
        return self

    def by_date_range(self, date_from=None, date_to=None):
        if date_from is not None or date_to is not None:
            def _date_filter(df):
                # Ensure 'day' is datetime
                if not np.issubdtype(df['day'].dtype, np.datetime64):
                    df = df.copy()
                    df['day'] = pd.to_datetime(df['day'], errors='coerce')

                mask = pd.Series(True, index=df.index)
                if date_from is not None:
                    mask &= df['day'] >= pd.to_datetime(date_from)
                if date_to is not None:
                    mask &= df['day'] <= pd.to_datetime(date_to)
                return mask

            self._filters.append(_date_filter)
        return self

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._filters:  # nothing to filter
            return df

        mask = pd.Series(True, index=df.index)
        for f in self._filters:
            mask &= f(df)

        return df[mask]

# df_filter = (
#     DataFrameFilter()
#     .by_categories(["Food", "Travel"])
#     .by_transaction_types(["Debit"])
# )
#
# filtered_df = df_filter.apply(df)

# def aggregate_accounts_balance():
