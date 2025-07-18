from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework import status, generics

from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend

from budget.serializers import (
    TransactionSerializer,
    ChartDataSerializer,
    BalanceHistorySerializer,
    BalanceHistoryRefreshSerializer,
    MoneyAccountSerializer,
    MonthlySummarySerializer,
    MonthlyCategorySummarySerializer,
    MonthlyParentCategorySummarySerializer,
    ParentCategorySerializer,
)
from budget.models import (
    Transaction,
    MoneyAccount,
    BalanceHistory,
    MonthlySummary,
    MonthlyCategorySummary,
    MonthlyParentCategorySummary,
    ParentCategory)
from budget.forms import BudgetExpenseEntryForm
from core.utils import update_request_data_for_transaction
from budget.filters import TransactionFilter, MonthlySummaryFilter, MonthlyCategorySummaryFilter, MonthlyParentCategorySummaryFilter


class BalanceHistoryRefreshAPIView(APIView):
    def get(self, request, money_account_name):
        serializer = BalanceHistoryRefreshSerializer(money_account_name)

        # return JsonResponse({'message': 'Balance history refreshed successfully'})  # can do as well
        return Response(serializer.data)


class BalanceHistoryAPIView(ListAPIView):
    serializer_class = BalanceHistorySerializer

    def get_queryset(self):
        money_account_name = self.kwargs['money_account_name']
        money_account = MoneyAccount.objects.get(name=money_account_name)
        queryset = BalanceHistory.objects.filter(money_account=money_account)
        return queryset


class ChartDataAPIView(APIView):
    def get(self, request, format=None):
        # summary, totals = create_yearly_summary(2025)
        # serializer = ChartDataSerializer(summary)

        return Response()


class MoneyAccountAPIView(generics.ListCreateAPIView):
    queryset = MoneyAccount.objects.all()
    serializer_class = MoneyAccountSerializer


class TransactionFormAPIView(APIView):
    def get(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        form = BudgetExpenseEntryForm(instance=transaction)
        form_html = render_to_string('budget/transaction_form.html', {'form': form})
        return HttpResponse(form_html)


class TransactionDuplicateAPIView(APIView):
    def post(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        data = update_request_data_for_transaction(request)

        serializer = TransactionSerializer(transaction, data=data, partial=True)

        if serializer.is_valid():
            new_transaction = serializer.save(pk=None)  # Create a new entry without a primary key
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionAPIView(APIView):
    def get(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        data = update_request_data_for_transaction(request)
        print(f'{transaction.origin = }')
        print(f'{transaction.destination = }')
        serializer = TransactionSerializer(transaction, data=data, partial=True)
        print(f'{data = }')
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Transaction updated successfully'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, transaction_id):
        # todo: figure out if also use a serializer?
        transaction = get_object_or_404(Transaction, id=transaction_id)
        transaction.delete()
        return Response({"message": "Transaction deleted successfully"}, status=status.HTTP_200_OK)


class TransactionsAPIView(generics.ListCreateAPIView):
    """
    You don’t need select_related() if you're only returning IDs and not accessing related object fields anywhere in the view, serializer, or filters.
    But — you’ll want it if:
    You access related fields like .origin.name, .category.name (which you might do soon).
    You add SerializerMethodFields that reference related fields.
    You use filters or annotations that touch related models.
    """
    queryset = Transaction.objects.select_related('origin', 'destination', 'category').all()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def filter_queryset(self, queryset):
        """For debugging"""
        # print("Raw GET params:", self.request.GET)
        filtered_qs = super().filter_queryset(queryset)
        # print("Filtered queryset SQL:", filtered_qs.query)
        return filtered_qs


class ParentCategoryAPIView(generics.ListCreateAPIView):
    queryset = ParentCategory.objects.all()
    serializer_class = ParentCategorySerializer
    filter_backends = [DjangoFilterBackend]


class MonthlySummaryAPIView(generics.ListCreateAPIView):
    queryset = MonthlySummary.objects.all()
    serializer_class = MonthlySummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MonthlySummaryFilter

    def get_queryset(self):
        queryset = MonthlySummary.objects.all()
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')

        if year is not None and month is not None:
            return queryset.filter(year=year, month=month)

        # Optionally: add support for query params if you want
        # year = self.request.query_params.get('year')
        # month = self.request.query_params.get('month')
        # if year and month:
        #     return queryset.filter(date__year=year, date__month=month)

        return queryset


class MonthlyCategorySummaryAPIView(generics.ListCreateAPIView):
    queryset = MonthlyCategorySummary.objects.all()
    serializer_class = MonthlyCategorySummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MonthlyCategorySummaryFilter


class MonthlyParentCategorySummaryAPIView(generics.ListCreateAPIView):
    queryset = MonthlyParentCategorySummary.objects.all()
    serializer_class = MonthlyParentCategorySummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MonthlyParentCategorySummaryFilter
