import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from . import kpi_calc, filters

DEFAULT_KPI_KEYS = ['INCOMING', 'OUTGOING', 'INNER', 'NUM_TRANSACTIONS', 'BALANCE', "BALANCE_REAL"]


def parse_date(date_str=None, mode='day'):
    if date_str:
        try:
            if mode == 'day':
                return datetime.strptime(date_str, '%d.%m.%Y')
            elif mode == 'month':
                return datetime.strptime(date_str, '%m.%Y')
            elif mode == 'year':
                return datetime.strptime(date_str, '%Y')
            else:
                raise ValueError("Mode must be 'day', 'month', or 'year'.")
        except ValueError:
            raise ValueError(f"Invalid date format for mode '{mode}'. Expected format: "
                             f"'dd.mm.yyyy' for day, 'mm.yyyy' for month, or 'yyyy' for year.")
    else:
        now = datetime.now()
        if mode == 'day':
            return now
        elif mode == 'month':
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif mode == 'year':
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError("Mode must be 'day', 'month', or 'year'.")


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


def get_all_time_date_range(daily_kpis):
    daily_kpis = prepare_kpi_df(daily_kpis, 'day')
    start_date = daily_kpis['day'].min().strftime('%d.%m.%Y')
    end_date = daily_kpis['day'].max().strftime('%d.%m.%Y')
    return f"{start_date} - {end_date}"


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
        chg_col = f"{key.lower()}_{prefix}_chg" if prefix else None
        pct_col = f"{key.lower()}_{prefix}_pct" if prefix else None

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
        date_range = get_all_time_date_range(daily_kpis)
    else:
        date_range = None

    return result, date_range



def get_kpis(granularity='day', date_str=None, transaction_types=None, parent_categories=None):
    date = parse_date(date_str, mode=granularity) if granularity != 'all' else None
    starting_balance = kpi_calc.get_starting_balance()
    # date_from = '2025-07-01'
    # date_to = '2025-07-31'
    # date_to = '2026-01-01'
    date_from = None
    date_to = None
    categories = None

    parent_categories = filters.get_parent_categories_names_list(parent_categories)

    apply_date_filters = date_from or date_to
    apply_filters: bool = filters.not_none_filters((categories, parent_categories, transaction_types))

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

        daily_kpis = get_daily_kpis(kpis, date, kpi_keys=DEFAULT_KPI_KEYS)

        print(pd.DataFrame.from_dict(daily_kpis[0]))

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

        monthly_kpis = get_monthly_kpis(monthly_kpis, date, kpi_keys=DEFAULT_KPI_KEYS)

        print(pd.DataFrame.from_dict(monthly_kpis[0]))

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

        yearly_kpis = get_yearly_kpis(yearly_kpis, date, kpi_keys=DEFAULT_KPI_KEYS)

        print(pd.DataFrame.from_dict(yearly_kpis[0]))

        return yearly_kpis

    elif granularity == 'all':
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
        all_time_kpis = get_all_time_kpis(kpis, daily_kpis, kpi_keys=DEFAULT_KPI_KEYS)

        print(pd.DataFrame.from_dict(all_time_kpis[0]))

        return all_time_kpis

    else:
        raise ValueError("Granularity must be 'day', 'month', 'year', or 'all'")
