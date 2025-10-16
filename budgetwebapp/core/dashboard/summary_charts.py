from core.dashboard import data_handling, data_pipeline


def get_summaries(date_unit='month', date_from=None, date_to=None,
                  apply_date_filters=False, apply_filters=False,
                  transaction_types=None, parent_categories=None, categories=None):
    pipeline = data_pipeline.SummaryPipeline()
    df = pipeline.load("summary_data")

    df = pipeline.apply_filters(
        df,
        date_from=date_from, date_to=date_to,
        apply_date=apply_date_filters, apply_data=apply_filters,
        transaction_types=transaction_types,
        parent_categories=parent_categories,
        categories=categories
    )

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
    df = data_handling.calculate_savings_rate(df)
    df = data_handling.accumulate_fields(df, ['income', 'expenses'])
    df = data_handling.calculate_volatility(df)

    df = df.replace([float('inf'), float('-inf')], 0).fillna(0)
    return df.to_dict(orient='list')
