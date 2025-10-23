from datetime import timedelta, date
from functools import reduce
from datetime import datetime
import pandas as pd


class Metric:

    @staticmethod
    def HPR(initial_value, profit, income=0):
        """ Holding period return, includes income (such as dividends)"""
        return profit / initial_value

    @staticmethod
    def simple_cagr(positions, time_strat='min'):
        """
        Calculate the simple annualized CAGR for a portfolio of positions.

        Parameters:
        - positions: QuerySet of positions, each with 'purchase_value', 'gross_pl', 'open_time'.
        - time_strat: str, either:
            - 'min' : annualize based on the earliest position's open_time.
            - 'avg' : annualize using the arithmetic mean of days held across all positions.

        Returns:
        - cagr: float, the annualized compound growth rate.

        Notes / Conclusions:
        1. Using 'min' (earliest date) treats the portfolio as if all capital
           was invested on the first open position. If after 20 days the portfolio's value went from 100% to 99.3%,
           we can annualize by dividing the year into 20-day intervals and compound: 0.993^(365.25 / 20) ≈ 0.8796.
           This means the portfolio would lose approximately 12.04% if the same performance continued for a full year.
        2. Using 'avg' takes the simple average of holding periods (in days)
           across all positions, so older positions still tend to stretch the
           annualized return more than very recent ones, i.e. older positions carry more weight.
           If average time is assumed to be 12 days, then 0.993^(365.25 / 20) ≈ 0.8075.
           This means that the portfolio would lose approximately 19.75% of its value, compared to 12.04% using 'min'.
        """
        if positions.empty:
            return 0.0

        total_purchase_value = positions['purchase_value'].sum()
        total_current_value = (positions['purchase_value'] + positions['gross_pl']).sum()

        if total_purchase_value <= 0:
            return 0.0

        today = datetime.now()

        if time_strat == 'min':
            earliest_date = positions['open_time'].min().normalize()
            years = (today - earliest_date).days / 365.25
        elif time_strat == 'avg':
            days_held = (today - positions['open_time'].dt.normalize()).dt.days
            years = days_held.mean() / 365.25
        else:
            raise ValueError("time_strat must be either 'min' or 'avg'")

        if years <= 0:
            return 0.0

        cagr = (total_current_value / total_purchase_value) ** (1 / years) - 1
        return cagr

    @staticmethod
    def time_weighted_cagr(positions):
        """
        Calculate the time-weighted annualized CAGR for a portfolio of positions.

        Parameters:
        - positions: list of dicts, each with:
            'purchase_value' (float), 'gross_pl' (float), 'open_time' (datetime)

        Returns:
        - cagr: float, the annualized compound growth rate weighted by both
          capital invested and time held.

        Notes / Conclusions:
        1. This method weights each position’s contribution to the overall CAGR
           by both its purchase value and the time it has been held. Positions
           with larger capital and longer holding periods have proportionally
           greater influence on the final annualized rate.
        2. The holding period for each position is converted into fractional years
           (days / 365.25), and the weighted average holding period is computed using
           purchase_value-weighted time.
        3. Compared to simple CAGR:
             - Simple CAGR assumes that all positions started together, or averages the holding time.
             - Time-weighted CAGR accounts for differing entry times and position sizes,
               producing a more accurate measure for portfolios with staggered investments.
        """
        if positions.empty:
            return 0.0

        now = datetime.now()

        # Holding time in fractional years
        positions = positions.copy()
        positions['holding_years'] = (now - positions['open_time']).dt.days / 365.25

        # Weighted average holding time (weighted by purchase_value)
        weighted_time_sum = (positions['purchase_value'] * positions['holding_years']).sum()
        purchase_value_sum = positions['purchase_value'].sum()
        total_value_sum = (positions['purchase_value'] + positions['gross_pl']).sum()

        if purchase_value_sum <= 0:
            return 0.0

        time_weighted_years = weighted_time_sum / purchase_value_sum

        if total_value_sum and time_weighted_years > 0:
            cagr = (total_value_sum / purchase_value_sum) ** (1 / time_weighted_years) - 1
        else:
            cagr = 0.0

        return cagr

    @staticmethod
    def twr(df, time_period='today'):
        if not pd.api.types.is_datetime64_any_dtype(df['Datetime']):
            df['Datetime'] = pd.to_datetime(df['Datetime'])

        df = df.sort_values('Datetime')
        max_time = df['Datetime'].max()

        if time_period == 'today':
            day_start = df['Datetime'].max().normalize()
            data = df[df['Datetime'] >= day_start].copy()
        elif time_period == 'last_24h':
            data = df[df['Datetime'] > max_time - pd.Timedelta(days=1)].copy()
        elif time_period == 'weekly':
            data = df.set_index('Datetime').resample('W').last().reset_index()
        elif time_period == 'last_week':
            data = df[df['Datetime'] > max_time - pd.Timedelta(weeks=1)].copy()
        elif time_period == 'monthly':
            data = df.set_index('Datetime').resample('M').last().reset_index()
        elif time_period == 'last_month':
            data = df[df['Datetime'] > max_time - pd.Timedelta(days=30)].copy()
        # todo: check weekly, monthly and introduce yearly
        elif time_period == 'last_year':
            data = df[df['Datetime'] > max_time - pd.Timedelta(days=365)].copy()
        elif time_period == 'total':
            data = df.copy()
        else:
            raise ValueError("time_strat must be either 'today', 'last_24h' or 'total'")

        # Find subperiods where cashflow changes
        data['input_shift'] = data['input_value_over_time'].shift()
        change_indices = data.index[(data['input_value_over_time'] != data['input_shift'])].to_list()

        # Always include first and last row
        change_indices = [data.index.min()] + change_indices + [data.index.max()]
        change_indices = sorted(set(change_indices))

        subperiods = []
        for i in range(len(change_indices) - 1):
            # pick rows for subperiod i
            start = data.loc[change_indices[i]]
            end = data.loc[change_indices[i + 1]]

            V_start = start['portfolio_value']
            V_end = end['portfolio_value']
            CF = end['input_value_over_time'] - start['input_value_over_time']

            if V_start > 0:
                subperiods.append(1 + (V_end - V_start - CF) / V_start)

        # Chain subperiods
        twr = 1
        for r in subperiods:
            twr *= r

        return twr - 1
