import django_filters
from django.db.models import Q

from budget.models import Transaction, Category, ParentCategory, MonthlySummary, MonthlyCategorySummary, MonthlyParentCategorySummary
from django import forms


class TransactionFilter(django_filters.FilterSet):
    transaction_type = django_filters.ChoiceFilter(
        choices=Transaction.TRANSACTION_TYPE_CHOICES,
        field_name='transaction_type',
        lookup_expr='iexact',
        empty_label='Any'
    )
    category = django_filters.ModelMultipleChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category',
        to_field_name='id',
        conjoined=False,
        # widget=django_filters.widgets.CSVWidget(),
        # method='filter_category'
    )
    parent_category = django_filters.ModelMultipleChoiceFilter(
        queryset=ParentCategory.objects.all(),
        method='filter_by_parent_category',
        label='Parent Category',
    )

    date_from = django_filters.DateFilter(
        field_name='date',
        lookup_expr='gte',
        label='From date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = django_filters.DateFilter(
        field_name='date',
        lookup_expr='lte',
        label='To date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def filter_category(self, queryset, name, value):
        if not value:
            return queryset.none()  # No categories selected = no results
        return queryset.filter(category__in=value)

    def filter_by_parent_category(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(category__parent_category__in=value)

    class Meta:
        model = Transaction
        fields = ('transaction_type', 'category', 'parent_category', 'date_from', 'date_to')


class MonthlySummaryFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter()
    # month = django_filters.NumberFilter()
    # min_income = django_filters.NumberFilter(field_name='income', lookup_expr='gte')
    # max_expenses = django_filters.NumberFilter(field_name='expenses', lookup_expr='lte')

    class Meta:
        model = MonthlySummary
        # fields = ['year', 'month', 'income', 'expenses']
        fields = ['year']

class MonthlyParentCategorySummaryFilter(django_filters.FilterSet):
    year = django_filters.NumberFilter(field_name='year')

    class Meta:
        model = MonthlyParentCategorySummary
        fields = ['year']