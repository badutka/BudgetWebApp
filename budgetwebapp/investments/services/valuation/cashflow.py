import pandas as pd
from investments.models import CashOperation
from .datetime_utils import standardize_datetime_by_period

def free_funds_over_time(account_type, period):
    cash_ops = CashOperation.objects.filter(account_type=account_type)
    df_cash_ops = pd.DataFrame({
        'time': [d.time for d in cash_ops],
        'amount': [d.amount for d in cash_ops]
    })
    df_cash_ops['time'] = standardize_datetime_by_period(df_cash_ops['time'], period)
    df_cumulative_cash = (
        df_cash_ops.groupby('time')['amount']
        .sum()
        .cumsum()
    )
    return df_cumulative_cash