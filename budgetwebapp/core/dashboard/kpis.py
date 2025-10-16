import pandas as pd

from core.dashboard import data_handling, data_pipeline
from core.constants import FREQ_MAP, KPI_COLS


def get_kpis(date_unit='month', date_for=None, date_from=None, date_to=None,
             apply_date_filters=False, apply_filters=False,
             transaction_types=None, parent_categories=None, categories=None):
    pipeline = data_pipeline.KpiPipeline()
    df = pipeline.load("kpi_data")

    date_unit = date_unit.lower() if date_unit and date_unit.lower() in FREQ_MAP else None
    freq = FREQ_MAP.get(date_unit)

    df = pipeline.apply_filters(
        df,
        date_from=date_from, date_to=date_to,
        apply_date=apply_date_filters, apply_data=apply_filters,
        transaction_types=transaction_types,
        parent_categories=parent_categories,
        categories=categories
    )

    df_agg = data_handling.group_kpis(df, group_by_col=date_unit, include_num_transactions=True)

    if date_unit:
        df_agg = data_handling.zero_fill_missing_ds(
            df_agg,
            ['income', 'expenses', 'inner', 'net_savings', 'num_transactions'],
            date_unit=date_unit,
            fill_to_start_of_year=True,
            fill_to_end_of_year=False,
            date_from=date_from,
            date_to=date_to,
            date_col=date_unit
        )

    df_agg['accounts_balance'] = data_handling.get_accounts_balance(df_agg)
    data_handling.add_change_metrics(df_agg, KPI_COLS)

    if date_unit:
        df_agg[date_unit] = pd.to_datetime(df_agg[date_unit])
        df_agg_row = df_agg[df_agg[date_unit].dt.to_period(freq) == pd.to_datetime(date_for).to_period(freq)]
        date_range = data_handling.get_comparison_date_range(date_for, date_unit)
    else:
        df_agg_row = df_agg
        start_date = pd.to_datetime(df['day']).min().strftime('%d.%m.%Y')
        end_date = pd.to_datetime(df['day']).max().strftime('%d.%m.%Y')
        date_range = f'{start_date} → {end_date}'

    df_agg_row = df_agg_row.iloc[0] if not df_agg_row.empty else None
    kpis = data_handling.build_kpi_result(df_agg_row, KPI_COLS, prefix='')

    return kpis, date_range
