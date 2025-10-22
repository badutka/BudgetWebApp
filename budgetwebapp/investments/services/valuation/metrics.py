from datetime import timedelta, date
from functools import reduce

from django.utils import timezone
from django.db.models import Sum, Min

from core.logger import logger


class Metric:

    @staticmethod
    def HPR(initial_value, profit, income=0):
        """ Holding period return, includes income (such as dividends)"""
        return profit / initial_value

    def SimpleCAGR(self):
        pass

    def ValueWeightedCAGR(self):
        pass

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
           annualized return more than very recent ones, i.e. older positions carry more weight
        3. This approach gives a more “middle-ground” annualization than min or max.
        4. Total return over the period (answers the "$1 question") is:
               total_return = (total_current_value / total_purchase_value) - 1
           Annualization scales this to a full year based on the chosen time strategy.
        """
        aggregates = positions.aggregate(
            total_purchase_value=Sum('purchase_value'),
            total_gross_pl=Sum('gross_pl'),
            earliest_purchase_date=Min('open_time')
        )

        total_purchase_value = aggregates['total_purchase_value'] or 0
        total_current_value = (aggregates['total_purchase_value'] or 0) + (aggregates['total_gross_pl'] or 0)
        earliest_purchase_date = aggregates['earliest_purchase_date']

        if total_purchase_value > 0 and earliest_purchase_date:
            if time_strat == 'min':
                years = (date.today() - earliest_purchase_date.date()).days / 365.25
            elif time_strat == 'avg':
                # simple average of holding periods (in years)
                now = date.today()
                days_list = [(now - pos.open_time.date()).days for pos in positions]
                avg_days = sum(days_list) / len(days_list) if days_list else 0
                years = avg_days / 365.25
            else:
                raise ValueError("time_strat must be either 'min' or 'avg'")

            if years > 0:
                cagr = (total_current_value / total_purchase_value) ** (1 / years) - 1
            else:
                cagr = 0
        else:
            cagr = 0

        return cagr

    @staticmethod
    def time_weighted_cagr(positions):
        now = timezone.now()

        weighted_time_sum = 0
        purchase_value_sum = 0
        total_value_sum = 0

        for pos in positions:
            # Time in years (fractional)
            holding_period_days = (now - pos.open_time).days
            holding_period_years = holding_period_days / 365.25  # approximate

            # Weighted sum
            weighted_time_sum += pos.purchase_value * holding_period_years
            purchase_value_sum += pos.purchase_value
            total_value_sum += pos.purchase_value + pos.gross_pl

            # logger.info(f'{holding_period_years = }')
            # logger.info(f'{pos.purchase_value = }')
            # logger.info(f'{pos.gross_pl = }')

        # Time-weighted average
        time_weighted_years = weighted_time_sum / purchase_value_sum if purchase_value_sum else 0

        # CAGR calculation
        if total_value_sum and time_weighted_years > 0:
            cagr = (total_value_sum / purchase_value_sum) ** (1 / time_weighted_years) - 1
        else:
            cagr = 0

        return cagr

    @staticmethod
    def time_weighted_return(positions):
        positions = positions.order_by('open_time')

        # # Initialize variables
        # sub_period_returns = []
        # portfolio_value = 0  # total value before each new position
        #
        # for pos in positions:
        #     # Current portfolio value before adding this new position
        #     start_value = portfolio_value
        #
        #     # Add this position's purchase value to portfolio
        #     portfolio_value += pos.purchase_value
        #
        #     # Calculate return for this sub-period (only on existing portfolio)
        #     if start_value > 0:
        #         # Existing portfolio grew by P/L of previous positions
        #         r = pos.gross_pl / start_value
        #         sub_period_returns.append(1 + r)
        #     else:
        #         # First position, no previous portfolio to grow
        #         sub_period_returns.append(1)
        #
        # # Compound all sub-period returns to get TWR
        # twr = reduce(lambda x, y: x * y, sub_period_returns) - 1
        # return twr

        # 2) gather all unique event dates (each open_time and today)
        event_dates = sorted({p.open_time.date() for p in positions} | {date.today()})
        today = date.today()

        sub_factors = []
        for i in range(len(event_dates) - 1):
            start_date = event_dates[i]
            end_date = event_dates[i + 1]

            # portfolio value just after start_date (i.e. include positions opened on or before start_date)
            V_start = sum(position_value_at(p, start_date) for p in positions if p.open_time.date() <= start_date)
            # value just before next inflow (i.e. at end_date, before any new inflow on end_date)
            V_end = sum(position_value_at(p, end_date) for p in positions if p.open_time.date() <= end_date)

            if V_start <= 0:
                # no portfolio to measure return on — treat as neutral factor 1 (or skip)
                factor = 1.0
            else:
                factor = V_end / V_start
            sub_factors.append(factor)

        twr = reduce(lambda a, b: a * b, sub_factors, 1.0) - 1.0
        print(f"TWR = {twr:.2%}")
