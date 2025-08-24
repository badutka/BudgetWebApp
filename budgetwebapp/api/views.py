from statistics import median
import numpy as np

from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework import status, generics

from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum

from budget import models, serializers, filters
from budget.forms import BudgetExpenseEntryForm
from core.utils import update_request_data_for_transaction


class BalanceHistoryRefreshAPIView(APIView):
    def get(self, request, money_account_name):
        serializer = serializers.BalanceHistoryRefreshSerializer(money_account_name)

        # return JsonResponse({'message': 'Balance history refreshed successfully'})  # can do as well
        return Response(serializer.data)


class BalanceHistoryAPIView(ListAPIView):
    serializer_class = serializers.BalanceHistorySerializer

    def get_queryset(self):
        money_account_name = self.kwargs['money_account_name']
        money_account = models.MoneyAccount.objects.get(name=money_account_name)
        queryset = models.BalanceHistory.objects.filter(money_account=money_account)
        return queryset


class ChartDataAPIView(APIView):
    def get(self, request, format=None):
        monthly_summaries = models.MonthlySummary.objects.all()
        serializer = serializers.MonthlySummarySerializer(monthly_summaries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MoneyAccountAPIView(generics.ListCreateAPIView):
    queryset = models.MoneyAccount.objects.all()
    serializer_class = serializers.MoneyAccountSerializer


class TransactionFormAPIView(APIView):
    def get(self, request, transaction_id):
        transaction = get_object_or_404(models.Transaction, id=transaction_id)
        form = BudgetExpenseEntryForm(instance=transaction)
        form_html = render_to_string('budget/transaction_form.html', {'form': form})
        return HttpResponse(form_html)


class TransactionsByCategoryAPIView(APIView):
    def get(self, request, category_id):
        transactions = models.Transaction.objects.filter(category_id=category_id)

        amounts = [float(a) for a in transactions.values_list('amount', flat=True)]

        total = round(sum(amounts), 2)
        count = len(amounts)
        _min = min(amounts)
        avg = round(total / count, 2) if count else 0
        med = round(median(amounts), 2) if count else 0
        perc10 = round(float(np.percentile(amounts, 10)), 2) if count else 0
        perc90 = round(float(np.percentile(amounts, 90)), 2) if count else 0
        _max = max(amounts)

        if count:
            first_date = transactions.first().date
            last_date = transactions.last().date
            delta_days = (first_date - last_date).days

            if delta_days <= 30:
                date_span_str = f"{delta_days} Days"
            else:
                months = round(delta_days / 30, 2)
                date_span_str = f"{months} Months"
        else:
            date_span_str = "0 Days"

        transactions_data = [
            {
                'date': txn.date,
                'description': txn.description,
                'amount': float(txn.amount),
            }
            for txn in transactions
        ]

        return Response({
            'transactions': transactions_data,
            'total': total,
            'count': count,
            'min': _min,
            'average': avg,
            'median': med,
            'percentile_10': perc10,
            'percentile_90': perc90,
            'max': _max,
            'date_span_str': date_span_str,
        })


class TransactionDuplicateAPIView(APIView):
    def post(self, request, transaction_id):
        transaction = get_object_or_404(models.Transaction, id=transaction_id)
        data = update_request_data_for_transaction(request)

        serializer = serializers.TransactionSerializer(transaction, data=data, partial=True)

        if serializer.is_valid():
            new_transaction = serializer.save(pk=None)  # Create a new entry without a primary key
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionAPIView(APIView):
    def get(self, request, transaction_id):
        transaction = get_object_or_404(models.Transaction, id=transaction_id)
        serializer = serializers.TransactionSerializer(transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, transaction_id):
        transaction = get_object_or_404(models.Transaction, id=transaction_id)
        data = update_request_data_for_transaction(request)
        print(f'{transaction.origin = }')
        print(f'{transaction.destination = }')
        serializer = serializers.TransactionSerializer(transaction, data=data, partial=True)
        print(f'{data = }')
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Transaction updated successfully'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, transaction_id):
        # todo: figure out if also use a serializer?
        transaction = get_object_or_404(models.Transaction, id=transaction_id)
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
    queryset = models.Transaction.objects.select_related('origin', 'destination', 'category').all()
    serializer_class = serializers.TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = filters.TransactionFilter

    def filter_queryset(self, queryset):
        """For debugging"""
        # print("Raw GET params:", self.request.GET)
        filtered_qs = super().filter_queryset(queryset)
        # print("Filtered queryset SQL:", filtered_qs.query)
        return filtered_qs


class ParentCategoryAPIView(generics.ListCreateAPIView):
    queryset = models.ParentCategory.objects.all()
    serializer_class = serializers.ParentCategorySerializer
    filter_backends = [DjangoFilterBackend]


class CategoryAPIView(generics.ListCreateAPIView):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.kwargs.get('category_id')

        if category_id:
            return queryset.filter(id=category_id)

        return queryset


class MonthlySummaryAPIView(generics.ListCreateAPIView):
    queryset = models.MonthlySummary.objects.all()
    serializer_class = serializers.MonthlySummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = filters.MonthlySummaryFilter

    def get_queryset(self):
        """This is used to make sure that starting balance for a new year is properly fetched"""
        queryset = super().get_queryset()
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        # print(f'{self.request.query_params = }')

        if year is not None and month is not None:
            return queryset.filter(year=year, month=month)

        # Optionally: add support for query params if you want
        # year = self.request.query_params.get('year')
        # month = self.request.query_params.get('month')
        # if year and month:
        #     return queryset.filter(date__year=year, date__month=month)

        return queryset


class MonthlyCategorySummaryAPIView(generics.ListCreateAPIView):
    queryset = models.MonthlyCategorySummary.objects.all()
    serializer_class = serializers.MonthlyCategorySummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = filters.MonthlyCategorySummaryFilter


class MonthlyParentCategorySummaryAPIView(generics.ListCreateAPIView):
    queryset = models.MonthlyParentCategorySummary.objects.all()
    serializer_class = serializers.MonthlyParentCategorySummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = filters.MonthlyParentCategorySummaryFilter
