import pandas as pd

from core.logger import logger


def calculate_chart_data(summaries):
    # Convert to DataFrame
    df = pd.DataFrame(summaries)

    # Convert numeric columns from strings to floats
    df[['income', 'expenses', 'net_savings', 'ending_balance']] = df[
        ['income', 'expenses', 'net_savings', 'ending_balance']].astype(float)

    df['savings_rate'] = round(df['net_savings'] / df['income'] * 100, 2)
    # logger.debug(df.to_dict(orient="records"))

    df = df.replace([float('inf'), float('-inf')], None)
    df = df.where(pd.notnull(df), None)
    logger.debug(df)
    return df.to_dict(orient="list")
