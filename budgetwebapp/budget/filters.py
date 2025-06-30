import django_filters
from django.db.models import Q

from budget.models import Transaction, Category
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

    class Meta:
        model = Transaction
        fields = ('transaction_type', 'category', 'date_from', 'date_to')
