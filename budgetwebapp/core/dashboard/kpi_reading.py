import pandas as pd
from datetime import timedelta

from core.logger import logger
from . import kpi_calc, filters as data_filters

DEFAULT_KPI_KEYS = ['INCOMING', 'OUTGOING', 'INNER', 'NUM_TRANSACTIONS', 'BALANCE', "BALANCE_REAL"]


def get_daily_date_range(date):
    return f"{(date - timedelta(days=1)).strftime('%d.%m.%Y')} - {date.strftime('%d.%m.%Y')}"


def get_monthly_date_range(current_month):
    # Previous month
    if current_month.month == 1:
        prev_month = current_month.replace(year=current_month.year - 1, month=12)
    else:
        prev_month = current_month.replace(month=current_month.month - 1)

    # Format range: "MM.YYYY - MM.YYYY"
    return f"{prev_month.strftime('%m.%Y')} - {current_month.strftime('%m.%Y')}"


def get_yearly_date_range(current_year):
    # Previous year
    prev_year = current_year - 1
    return f"{prev_year} - {current_year}"


def prepare_kpi_df(kpis, col):
    kpis[col] = pd.to_datetime(kpis[col])
    kpis = kpis.fillna('N/A')
    return kpis


def get_all_time_date_range(daily_kpis=None) -> tuple[str, str]:
    if daily_kpis is None:
        daily_kpis = pd.read_csv('../artifacts/data/daily_kpis.csv')
    daily_kpis = prepare_kpi_df(daily_kpis, 'day')
    start_date = daily_kpis['day'].min().strftime('%d.%m.%Y')
    end_date = daily_kpis['day'].max().strftime('%d.%m.%Y')
    return start_date, end_date

def build_kpi_result(row, kpi_keys, prefix=None):
    result = {}

    if row is None:
        for key in kpi_keys:
            result[key] = {
                'amount': 0,
                'change': 0,
                'pct_change': "N/A"
            }
        return result

    for key in kpi_keys:
        amt_col = key
        chg_col = f"{key.lower()}_{prefix}_chg"
        pct_col = f"{key.lower()}_{prefix}_pct"
        result[key] = {
            'amount': row.get(amt_col, 0) if pd.notna(row.get(amt_col)) else 0,
            'change': row.get(chg_col, 0) if chg_col and pd.notna(row.get(chg_col)) else 0,
            'pct_change': row.get(pct_col, "N/A") if pct_col and pd.notna(row.get(pct_col)) else "N/A"
        }

    return result


def get_daily_kpis(daily_kpis, date, kpi_keys):
    daily_kpis = prepare_kpi_df(daily_kpis, 'day')

    daily_row = daily_kpis[daily_kpis['day'].dt.date == date.date()]
    date_range = get_daily_date_range(date)

    row = daily_row.iloc[0] if not daily_row.empty else None
    result = build_kpi_result(row, kpi_keys, prefix='dod')

    return result, date_range


def get_monthly_kpis(monthly_kpis, date, kpi_keys):
    monthly_kpis = prepare_kpi_df(monthly_kpis, 'month')

    current_month = date.replace(day=1)

    monthly_row = monthly_kpis[
        (monthly_kpis['month'].dt.year == current_month.year) &
        (monthly_kpis['month'].dt.month == current_month.month)
        ]

    date_range = get_monthly_date_range(current_month)
    row = monthly_row.iloc[0] if not monthly_row.empty else None

    result = build_kpi_result(row, kpi_keys, prefix='mom')

    return result, date_range


def get_yearly_kpis(yearly_kpis, date, kpi_keys):
    yearly_kpis = prepare_kpi_df(yearly_kpis, 'year')
    current_year = date.year

    yearly_row = yearly_kpis[yearly_kpis['year'].dt.year == current_year]

    date_range = get_yearly_date_range(current_year)
    row = yearly_row.iloc[0] if not yearly_row.empty else None

    result = build_kpi_result(row, kpi_keys, prefix='yoy')

    return result, date_range


def get_all_time_kpis(totals_kpis, daily_kpis, kpi_keys):
    # In other cases this row was of type 'object' and preserved types
    # In this case there are no N/As, so the row would be a pd.Series of floats.
    # This way we can preserve types
    row = {col: totals_kpis[col].iloc[0] for col in totals_kpis.columns}

    result = build_kpi_result(row, kpi_keys, prefix=None)

    if not daily_kpis.empty:
        start_date, end_date = get_all_time_date_range(daily_kpis)
        date_range = f'{start_date} - {end_date}'
    else:
        date_range = None

    return result, date_range

from core.dashboard_data.charts import zero_fill_missing_ds

def get_kpis(granularity='month', date_for=None, date_from=None, date_to=None, apply_date_filters=False, apply_filters=False, transaction_types=None, parent_categories=None, categories=None):
    starting_balance = kpi_calc.get_starting_balance()

    if granularity == 'day':
        suffix = 'dod'
        if apply_date_filters:
            kpis = pd.read_csv('../artifacts/data/kpis_detailed.csv')
            kpis = kpi_calc.calculate_kpis_between_dates(
                kpis,
                group_by_col=granularity,
                transaction_types=transaction_types,
                categories=categories,
                parent_categories=parent_categories,
                date_from=date_from,
                date_to=date_to,
                starting_balance=starting_balance,
                suffix=suffix
            )
        elif apply_filters:
            kpis = pd.read_csv('../artifacts/data/daily_kpis_detailed.csv')
            kpis = kpi_calc.calculate_kpis(
                kpis,
                group_by_col=granularity,
                transaction_types=transaction_types,
                categories=categories,
                parent_categories=parent_categories,
                starting_balance=starting_balance,
                suffix=suffix
            )
        else:
            kpis = pd.read_csv('../artifacts/data/daily_kpis.csv')

        daily_kpis = get_daily_kpis(kpis, date_for, kpi_keys=DEFAULT_KPI_KEYS)

        # print(pd.DataFrame.from_dict(daily_kpis[0]))
        # logger.info(pd.DataFrame.from_dict(daily_kpis[0]))

        return daily_kpis

    elif granularity == 'month':
        suffix = 'mom'
        if apply_date_filters:
            monthly_kpis = pd.read_csv('../artifacts/data/kpis_detailed.csv')
            monthly_kpis = kpi_calc.calculate_kpis_between_dates(
                monthly_kpis,
                group_by_col=granularity,
                transaction_types=transaction_types,
                categories=categories,
                parent_categories=parent_categories,
                date_from=date_from,
                date_to=date_to,
                starting_balance=starting_balance,
                suffix=suffix
            )
        elif apply_filters:
            monthly_kpis = pd.read_csv('../artifacts/data/monthly_kpis_detailed.csv')
            monthly_kpis = kpi_calc.calculate_kpis(
                monthly_kpis,
                group_by_col=granularity,
                transaction_types=transaction_types,
                categories=categories,
                parent_categories=parent_categories,
                starting_balance=starting_balance,
                suffix=suffix
            )
        else:
            monthly_kpis = pd.read_csv('../artifacts/data/monthly_kpis.csv')

        logger.info(f'\n{monthly_kpis}')

        monthly_kpis = get_monthly_kpis(monthly_kpis, date_for, kpi_keys=DEFAULT_KPI_KEYS)

        logger.info(f'\n{pd.DataFrame.from_dict(monthly_kpis[0])}')
        logger.info(pd.DataFrame.from_dict(monthly_kpis[0]))

        return monthly_kpis

    elif granularity == 'year':
        suffix = 'yoy'
        if apply_date_filters:
            yearly_kpis = pd.read_csv('../artifacts/data/kpis_detailed.csv')
            yearly_kpis = kpi_calc.calculate_kpis_between_dates(
                yearly_kpis,
                group_by_col=granularity,
                transaction_types=transaction_types,
                categories=categories,
                parent_categories=parent_categories,
                date_from=date_from,
                date_to=date_to,
                starting_balance=starting_balance,
                suffix=suffix
            )
        elif apply_filters:
            yearly_kpis = pd.read_csv('../artifacts/data/yearly_kpis_detailed.csv')
            yearly_kpis = kpi_calc.calculate_kpis(
                yearly_kpis,
                group_by_col=granularity,
                transaction_types=transaction_types,
                categories=categories,
                parent_categories=parent_categories,
                starting_balance=starting_balance,
                suffix=suffix
            )
        else:
            yearly_kpis = pd.read_csv('../artifacts/data/yearly_kpis.csv')

        yearly_kpis = get_yearly_kpis(yearly_kpis, date_for, kpi_keys=DEFAULT_KPI_KEYS)

        # print(pd.DataFrame.from_dict(yearly_kpis[0]))

        return yearly_kpis

    elif granularity == 'all_time':
        if apply_date_filters:
            kpis = pd.read_csv('../artifacts/data/kpis_detailed.csv')
            kpis = kpi_calc.calculate_kpis_between_dates(
                kpis,
                categories=categories,
                transaction_types=transaction_types,
                parent_categories=parent_categories,
                date_from=date_from,
                date_to=date_to,
                starting_balance=starting_balance
            )
        elif apply_filters:
            kpis = pd.read_csv('../artifacts/data/totals_kpis_detailed.csv')
            kpis = kpi_calc.calculate_kpis(
                kpis,
                categories=categories,
                transaction_types=transaction_types,
                parent_categories=parent_categories,
                starting_balance=starting_balance
            )
        else:
            kpis = pd.read_csv('../artifacts/data/totals_kpis.csv')

        daily_kpis = pd.read_csv('../artifacts/data/daily_kpis.csv')

        logger.info(f'\n{kpis}')

        all_time_kpis = get_all_time_kpis(kpis, daily_kpis, kpi_keys=DEFAULT_KPI_KEYS)

        logger.info(pd.DataFrame.from_dict(all_time_kpis[0]))

        return all_time_kpis

    else:
        raise ValueError("Granularity must be 'day', 'month', 'year', or 'all'")


from core.dashboard_data.charts import group_kpis

# def get_monthly_kpis(monthly_kpis, date, kpi_keys):
#     monthly_kpis = prepare_kpi_df(monthly_kpis, 'month')
#
#     current_month = date.replace(day=1)
#
#     monthly_row = monthly_kpis[
#         (monthly_kpis['month'].dt.year == current_month.year) &
#         (monthly_kpis['month'].dt.month == current_month.month)
#         ]
#
#     date_range = get_monthly_date_range(current_month)
#     row = monthly_row.iloc[0] if not monthly_row.empty else None
#
#     result = build_kpi_result(row, kpi_keys, prefix='mom')
#
#     return result, date_range

# def get_date_range(current_date, date_unit):
#     if date_unit == 'month':
#         if current_date.month == 1:
#             prev_month = current_date.replace(year=current_date.year - 1, month=12)
#         else:
#             prev_month = current_date.replace(month=current_date.month - 1)
#
#         # Format range: "MM.YYYY - MM.YYYY"
#         return f"{prev_month.strftime('%m.%Y')} - {current_date.strftime('%m.%Y')}"

freq_map = {
    "day": "D",
    "daily": "D",
    "month": "M",
    "monthly": "M",
    "year": "Y",
    "yearly": "Y",
    "week": "W",
    "weekly": "W",
}

fmt_map = {
    "D": "%d.%m.%Y",
    "W": "%d.%m.%Y",
    "M": "%m.%Y",
    "Q": "Q%q %Y",
    "Y": "%Y",
}

def get_comparison_date_range(date_for, freq):
    """
    Returns a compact comparison date range string based on frequency.
    Example:
      freq='M' or 'month' → '08.2025 - 09.2025'
      freq='D' or 'day'   → '05.10.2025 - 06.10.2025'
      freq='Y' or 'year'  → '2024 - 2025'
    """
    freq = freq_map.get(freq.lower(), freq.upper())

    date_for = pd.to_datetime(date_for)
    period = date_for.to_period(freq)
    prev_period = period - 1

    fmt = fmt_map.get(freq, "%Y-%m-%d")

    prev_str = prev_period.start_time.strftime(fmt)
    curr_str = period.start_time.strftime(fmt)

    return f"{prev_str} → {curr_str}"



def get_date_range(date_for, granularity):
    """
    Returns a formatted date range string for a given date and granularity.
    Works for 'day', 'month', 'year', or any pandas frequency like 'D', 'M', 'Y', 'W', etc.
    """
    freq_map = {
        "day": "D",
        "daily": "D",
        "month": "M",
        "monthly": "M",
        "year": "Y",
        "yearly": "Y",
        "week": "W",
        "weekly": "W",
    }

    freq = freq_map.get(granularity.lower(), granularity.upper())  # allow 'M', 'Y', etc.
    period = pd.to_datetime(date_for).to_period(freq)

    start = period.start_time.date()
    end = period.end_time.date()

    return f"{start}" if start == end else f"{start} → {end}"

def get_kpis_new(granularity='month', date_for=None, date_from=None, date_to=None, apply_date_filters=False, apply_filters=False, transaction_types=None, parent_categories=None, categories=None):
    starting_balance = kpi_calc.get_starting_balance()
    df = pd.read_csv('../artifacts/data/kpis_detailed.csv')
    cols = ['INCOMING', 'OUTGOING', 'INNER', 'NUM_TRANSACTIONS', 'BALANCE', 'BALANCE_REAL']

    granularity = None if granularity == 'all_time' else granularity

    if granularity == 'day':
        suffix = 'dod'
        freq = 'D'
    elif granularity == 'month':
        suffix = 'mom'
        freq = 'M'
    elif granularity == 'year':
        suffix = 'yoy'
        freq = 'Y'
    else:
        suffix = None
        granularity = None
        freq = None

    df_filter = data_filters.DataFilter()

    if apply_filters:
        (df_filter.by_transaction_types(transaction_types)
            .by_parent_categories(parent_categories)
            .by_categories(categories))

    if apply_date_filters:
        df_filter.by_date_range(date_from, date_to)

    df = df_filter.apply(df)

    df_agg = group_kpis(df, group_by_col=granularity)

    df_agg = kpi_calc.calculate_accounts_balance(df_agg, starting_balance)

    kpi_calc.add_change_metrics(df_agg, cols)

    if granularity:
        df_agg[granularity] = pd.to_datetime(df_agg[granularity])
        logger.info(f'\n{df_agg = }')
        df_agg_row = df_agg[df_agg[granularity].dt.to_period(freq) == pd.to_datetime(date_for).to_period(freq)]
        date_range = get_comparison_date_range(date_for, granularity)
    else:
        df_agg_row = df_agg.copy()
        start_date = pd.to_datetime(df['day']).min().strftime('%d.%m.%Y')
        end_date = pd.to_datetime(df['day']).max().strftime('%d.%m.%Y')
        date_range = f'{start_date} → {end_date}'

    logger.info(f'\n{df_agg_row = }')

    df_agg_row = df_agg_row.iloc[0] if not df_agg_row.empty else None
    kpis = build_kpi_result(df_agg_row, cols, prefix='')

    logger.info(f'\n{pd.DataFrame.from_dict(kpis)}')

    return kpis, date_range