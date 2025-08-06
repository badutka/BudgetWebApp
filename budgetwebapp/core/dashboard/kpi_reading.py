import pandas as pd
import numpy as np
from datetime import datetime, timedelta


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


def get_all_time_date_range(daily_kpis):
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


def get_daily_kpis(daily_kpis, date):
    kpi_keys = ['INCOMING', 'OUTGOING', 'INNER']
    daily_row = daily_kpis[daily_kpis['day'].dt.date == date.date()]
    date_range = get_daily_date_range(date)

    row = daily_row.iloc[0] if not daily_row.empty else None
    result = build_kpi_result(row, kpi_keys, prefix='dod')

    return result, date_range


def get_monthly_kpis(monthly_kpis, date):
    kpi_keys = ['INCOMING', 'OUTGOING', 'INNER']
    current_month = date.replace(day=1)

    monthly_row = monthly_kpis[
        (monthly_kpis['month'].dt.year == current_month.year) &
        (monthly_kpis['month'].dt.month == current_month.month)
        ]

    date_range = get_monthly_date_range(current_month)
    row = monthly_row.iloc[0] if not monthly_row.empty else None

    result = build_kpi_result(row, kpi_keys, prefix='mom')

    return result, date_range


def get_yearly_kpis(yearly_kpis, date):
    kpi_keys = ['INCOMING', 'OUTGOING', 'INNER']
    current_year = date.year

    yearly_row = yearly_kpis[yearly_kpis['year'].dt.year == current_year]

    date_range = get_yearly_date_range(current_year)
    row = yearly_row.iloc[0] if not yearly_row.empty else None

    result = build_kpi_result(row, kpi_keys, prefix='yoy')

    return result, date_range


def get_all_time_kpis(totals_kpis, daily_kpis):
    kpi_keys = ['INCOMING', 'OUTGOING', 'INNER']
    row = totals_kpis.iloc[0] if not totals_kpis.empty else None

    result = build_kpi_result(row, kpi_keys, prefix=None)

    if not daily_kpis.empty:
        date_range = get_all_time_date_range(daily_kpis)
    else:
        date_range = None

    return result, date_range



def get_kpis(granularity='day', date_str=None):
    def prepare_kpi_df(kpis, col):
        kpis[col] = pd.to_datetime(kpis[col])
        kpis = kpis.fillna('N/A')
        return kpis

    date = parse_date(date_str, mode=granularity) if granularity != 'all' else None

    if granularity == 'day':
        daily_kpis = pd.read_csv('daily_kpis.csv')
        daily_kpis = prepare_kpi_df(daily_kpis, 'day')
        return get_daily_kpis(daily_kpis, date)
    elif granularity == 'month':
        monthly_kpis = pd.read_csv('monthly_kpis.csv')
        monthly_kpis = prepare_kpi_df(monthly_kpis, 'month')
        return get_monthly_kpis(monthly_kpis, date)
    elif granularity == 'year':
        yearly_kpis = pd.read_csv('yearly_kpis.csv')
        yearly_kpis = prepare_kpi_df(yearly_kpis, 'year')
        return get_yearly_kpis(yearly_kpis, date)
    elif granularity == 'all':
        daily_kpis = pd.read_csv('daily_kpis.csv')
        daily_kpis = prepare_kpi_df(daily_kpis, 'day')
        totals_kpis = pd.read_csv('totals_kpis.csv')
        return get_all_time_kpis(totals_kpis, daily_kpis)
    else:
        raise ValueError("Granularity must be 'day', 'month', 'year', or 'all'")
