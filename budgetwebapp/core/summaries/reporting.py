from django.db.models import Sum, Q
from decimal import Decimal
from typing import Dict, List, Tuple

from budget.models import (
    Transaction,
    Category,
    ParentCategory,
    MonthlySummary,
    MonthlyCategorySummary,
    MonthlyParentCategorySummary,
    MoneyAccount
)


class ReportsUtility:
    """
    Utility functions to assist with managing reports and summaries,
    including deletion and year-specific checks.
    """

    @staticmethod
    def delete_existing_summary(year: int, month: int) -> None:
        """
        Deletes all monthly summaries for the given year and month.
        Useful before recalculating summaries to prevent duplication.
        """
        MonthlySummary.objects.filter(year=year, month=month).delete()
        MonthlyCategorySummary.objects.filter(year=year, month=month).delete()
        MonthlyParentCategorySummary.objects.filter(year=year, month=month).delete()

    @staticmethod
    def delete_summaries_if_year_empty(year: int) -> None:
        """
        Deletes all summaries for a given year if no transactions exist for that year.
        """
        if not Transaction.objects.filter(date__year=year).exists():
            MonthlySummary.objects.filter(year=year).delete()
            MonthlyCategorySummary.objects.filter(year=year).delete()
            MonthlyParentCategorySummary.objects.filter(year=year).delete()

    @staticmethod
    def is_new_transaction_year(year: int, created: bool, instance: Transaction) -> bool:
        """
        Checks whether a newly created transaction is the first in its year.

        :param year: Year of the transaction.
        :param created: Whether the instance was newly created.
        :param instance: The transaction instance.
        :return: True if it's the first transaction in the given year.
        """
        return created and not Transaction.objects.filter(
            date__year=year
        ).exclude(pk=instance.pk).exists()


class MonthlyReportBuilder:
    """
    Responsible for computing and updating monthly financial summaries.
    """

    @staticmethod
    def update_monthly_summary(year: int, month: int) -> None:
        """
        Updates the monthly summary, including income, expenses, net savings,
        ending balance, and adjusts future months accordingly.
        """
        print(f'Updating {year = }, {month = }')

        income = MonthlyReportBuilder._get_income_for_month(year, month)
        expenses = MonthlyReportBuilder._get_expenses_for_month(year, month)
        net_savings = income - expenses
        previous_ending_balance = MonthlyReportBuilder._get_previous_ending_balance(year, month)
        ending_balance = previous_ending_balance + net_savings

        summary, _ = MonthlyReportBuilder._update_current_month_summary(
            year, month, income, expenses, net_savings, ending_balance
        )

        MonthlyReportBuilder._update_future_months_summary(
            year, month, current_balance=ending_balance
        )

    @staticmethod
    def _get_income_for_month(year: int, month: int) -> Decimal:
        """
        Returns the total income for a given month.
        """
        return Transaction.objects.filter(
            date__year=year,
            date__month=month,
            category__transaction_type='INCOMING'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @staticmethod
    def _get_expenses_for_month(year: int, month: int) -> Decimal:
        """
        Returns the total expenses for a given month.
        """
        return Transaction.objects.filter(
            date__year=year,
            date__month=month,
            category__transaction_type='OUTGOING'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @staticmethod
    def _get_previous_ending_balance(year: int, month: int) -> Decimal:
        """
        Returns the ending balance from the most recent month before the given one.
        Falls back to the total of starting balances if no previous summary exists.
        """
        previous_summary = (
            MonthlySummary.objects
            .filter(year__lte=year)
            .exclude(year=year, month__gte=month)
            .order_by('-year', '-month')
            .first()
        )

        if previous_summary:
            return previous_summary.ending_balance

        return MoneyAccount.objects.aggregate(total=Sum('starting_balance'))['total'] or Decimal('0.00')

    @staticmethod
    def _update_current_month_summary(
        year: int,
        month: int,
        income: Decimal,
        expenses: Decimal,
        net_savings: Decimal,
        ending_balance: Decimal
    ) -> Tuple[MonthlySummary, bool]:
        """
        Inserts or updates the MonthlySummary entry for the given month.
        """
        return MonthlySummary.objects.update_or_create(
            year=year,
            month=month,
            defaults={
                'income': income,
                'expenses': expenses,
                'net_savings': net_savings,
                'ending_balance': ending_balance,
            }
        )

    @staticmethod
    def _update_future_months_summary(year: int, month: int, current_balance: Decimal) -> None:
        """
        Updates ending balances for all future monthly summaries after the given month.
        """
        future_months = MonthlySummary.objects.filter(
            Q(year__gt=year) | Q(year=year, month__gt=month)
        ).order_by('year', 'month')

        for future in future_months:
            future.ending_balance = current_balance + future.net_savings
            current_balance = future.ending_balance
            future.save(update_fields=['ending_balance'])


class MonthlyCategoryReportBuilder:
    """
    Handles generation of monthly summaries for each category.

    By default, this builder supports all three transaction types:
    OUTGOING, INCOMING, and INNER — without needing any reassignment or filtering.

    The monthly_summary_detailed.get_summary_detailed view helper handles these three types directly,
    so there's no need to remap or consolidate transaction types at the summary level.

    To add a new category summary:
    - Just create a Transaction of the appropriate type (OUTGOING, INCOMING, or INNER)
    - Then run this summary builder to reflect the changes
    """

    @staticmethod
    def update_monthly_category_summary(year: int, month: int) -> None:
        """
        Builds category-level summaries for a given month,
        ensuring all known categories are represented—even with zero amount.

        This includes all categories of all transaction types (OUTGOING, INCOMING, INNER).
        """
        all_categories = MonthlyCategoryReportBuilder._get_all_categories()
        category_totals = MonthlyCategoryReportBuilder._get_category_totals(year, month)
        totals_lookup = MonthlyCategoryReportBuilder._build_totals_lookup(category_totals)
        MonthlyCategoryReportBuilder._update_or_create_summaries(year, month, all_categories, totals_lookup)

    @staticmethod
    def _get_all_categories() -> List[Category]:
        # Returns all categories including their parent_category relation
        return Category.objects.select_related('parent_category')

    @staticmethod
    def _get_category_totals(year: int, month: int):
        # Aggregates transaction amounts grouped by (parent_category, category, transaction_type)
        return (
            Transaction.objects
            .filter(date__year=year, date__month=month)
            .values(
                'category__parent_category__name',
                'category__name',
                'category__transaction_type'
            )
            .annotate(amount=Sum('amount'))
        )

    @staticmethod
    def _build_totals_lookup(category_totals) -> Dict[Tuple[str, str, str], Decimal]:
        # Creates a lookup dictionary for quick (parent, category, type) -> amount mapping
        return {
            (
                item['category__parent_category__name'],
                item['category__name'],
                item['category__transaction_type'],
            ): item['amount']
            for item in category_totals
        }

    @staticmethod
    def _update_or_create_summaries(year: int, month: int, all_categories: List[Category], totals_lookup: Dict) -> None:
        # Iterates through all known categories and creates or updates summary records
        for category in all_categories:
            key = (
                category.parent_category.name,
                category.name,
                category.transaction_type,
            )
            amount = totals_lookup.get(key, Decimal('0.00'))

            MonthlyCategorySummary.objects.update_or_create(
                year=year,
                month=month,
                parent_category_name=category.parent_category.name,
                category_name=category.name,
                transaction_type=category.transaction_type,
                defaults={'amount': amount}
            )


class MonthlyParentCategoryReportBuilder:
    """
    Responsible for generating monthly summaries for parent categories.

    - All parent categories are always included in the OUTGOING section of the summary,
      regardless of whether they had any actual transactions that month.
    - INCOMING and INNER sections are populated only if transactions of those types exist
      for a parent category.
    """

    @staticmethod
    def update_monthly_parent_category_summary(year: int, month: int) -> None:
        """
        Updates or creates monthly summary records for all parent categories.

        Uses all defined ParentCategory objects to determine which parents to include in
        the OUTGOING section (ensuring nothing is left out even if no transactions exist).
        INCOMING and INNER summaries are built only if related transactions are found.
        """
        all_parent_names = MonthlyParentCategoryReportBuilder._get_all_parent_names()
        incoming_parents = MonthlyParentCategoryReportBuilder._get_incoming_parent_names()
        inner_parents = MonthlyParentCategoryReportBuilder._get_inner_parent_names()

        monthly_totals = MonthlyParentCategoryReportBuilder._get_monthly_totals(year, month)

        MonthlyParentCategoryReportBuilder._update_outgoing_summaries(year, month, all_parent_names, monthly_totals)
        MonthlyParentCategoryReportBuilder._update_incoming_summaries(year, month, incoming_parents, monthly_totals)
        MonthlyParentCategoryReportBuilder._update_inner_summaries(year, month, inner_parents, monthly_totals)

    @staticmethod
    def _get_all_parent_names():
        # Returns all parent category names from the ParentCategory model directly.
        # This ensures a stable list of parent categories for the OUTGOING section,
        # even if there are no related transactions in the given month.
        #
        # NOTE: If you want this to be based only on transactions (e.g., for a cleaner view),
        # you can use the commented-out code below instead. If you do that, make sure to call
        # `remove_parent_summary_on_last_object_delete` from the post_delete signal to clean up
        # summaries for removed parent categories.
        #
        # return (
        #     Transaction.objects
        #     .order_by('category__parent_category__name')  # required by distinct to work properly
        #     .values_list('category__parent_category__name', flat=True)
        #     .distinct()
        # )
        return (
            ParentCategory.objects
            .order_by('name')  # required by distinct to work properly
            .values_list('name', flat=True)
            .distinct()
        )

    @staticmethod
    def _get_incoming_parent_names() -> set:
        # Returns parent category names that have at least one INCOMING transaction
        return set(
            Transaction.objects
            .filter(category__transaction_type='INCOMING')
            .order_by('category__parent_category__name')
            .values_list('category__parent_category__name', flat=True)
            .distinct()
        )

    @staticmethod
    def _get_inner_parent_names() -> set:
        # Returns parent category names that have at least one INNER transaction
        return set(
            Transaction.objects
            .filter(category__transaction_type='INNER')
            .order_by('category__parent_category__name')
            .values_list('category__parent_category__name', flat=True)
            .distinct()
        )

    @staticmethod
    def _get_monthly_totals(year: int, month: int) -> Dict[Tuple[str, str], Decimal]:
        # Aggregates total amounts per (parent_category, transaction_type) for the given month
        raw_totals = (
            Transaction.objects
            .filter(date__year=year, date__month=month)
            .values('category__parent_category__name', 'category__transaction_type')
            .annotate(amount=Sum('amount'))
        )
        return {
            (item['category__parent_category__name'], item['category__transaction_type']): item['amount']
            for item in raw_totals
        }

    @staticmethod
    def _update_outgoing_summaries(year: int, month: int, parent_names, totals_lookup: Dict) -> None:
        # Create/update OUTGOING summary for every known parent category
        for parent_name in parent_names:
            amount = totals_lookup.get((parent_name, 'OUTGOING'), Decimal('0.00'))
            MonthlyParentCategorySummary.objects.update_or_create(
                year=year,
                month=month,
                parent_category_name=parent_name,
                transaction_type='OUTGOING',
                defaults={'amount': amount}
            )

    @staticmethod
    def _update_incoming_summaries(year: int, month: int, parent_names, totals_lookup: Dict) -> None:
        # Only update/create INCOMING summaries for parent categories that had incoming transactions
        for parent_name in parent_names:
            amount = totals_lookup.get((parent_name, 'INCOMING'), Decimal('0.00'))
            MonthlyParentCategorySummary.objects.update_or_create(
                year=year,
                month=month,
                parent_category_name=parent_name,
                transaction_type='INCOMING',
                defaults={'amount': amount}
            )

    @staticmethod
    def _update_inner_summaries(year: int, month: int, parent_names, totals_lookup: Dict) -> None:
        # INNER summaries may conceptually belong to either INCOMING or OUTGOING,
        # so they are duplicated across both types for now (see todo).
        for parent_name in parent_names:
            for t9n_type in ['OUTGOING', 'INCOMING']:
                amount = totals_lookup.get((parent_name, 'INNER'), Decimal('0.00'))
                MonthlyParentCategorySummary.objects.update_or_create(
                    year=year,
                    month=month,
                    parent_category_name=parent_name,
                    transaction_type=t9n_type, # todo: create separate inner summary objects for inner t9ns
                    defaults={'amount': amount}
                )


def update_all_summaries(year: int, month: int) -> None:
    """
    Entry point to update all summaries for a specific month and year.
    """
    MonthlyReportBuilder.update_monthly_summary(year, month)
    MonthlyParentCategoryReportBuilder.update_monthly_parent_category_summary(year, month)
    MonthlyCategoryReportBuilder.update_monthly_category_summary(year, month)


def remove_parent_summary_on_last_object_delete(year: int, month: int, instance: Transaction) -> None:
    """
    Deletes monthly summary records for a parent category if its last transaction
    in the given month was just deleted.

    This is only necessary if your summary builder (_get_all_parent_names) is **based on
    existing transactions**, rather than all ParentCategory objects.

    If you're using the ParentCategory model directly (as above), this function
    becomes redundant — but it's still safe to call just in case you change strategy later.
    """
    parent_name = instance.category.parent_category.name

    still_exists = Transaction.objects.filter(
        date__year=year,
        date__month=month,
        category__parent_category__name=parent_name
    ).exists()

    if not still_exists:
        MonthlyParentCategorySummary.objects.filter(
            year=year,
            month=month,
            parent_category_name=parent_name
        ).delete()