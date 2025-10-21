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
    def simple_cagr(positions):
        aggregates = positions.aggregate(
            total_purchase_value=Sum('purchase_value'),
            total_gross_pl=Sum('gross_pl'),
            earliest_purchase_date=Min('open_time')
        )

        total_purchase_value = aggregates['total_purchase_value'] or 0
        total_current_value = (aggregates['total_purchase_value'] or 0) + (aggregates['total_gross_pl'] or 0)
        earliest_purchase_date = aggregates['earliest_purchase_date']

        if total_purchase_value > 0 and earliest_purchase_date:
            years = (date.today() - earliest_purchase_date.date()).days / 365.25
            cagr = (total_current_value / total_purchase_value) ** (1 / years) - 1
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