from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework import status, generics

from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.http import HttpResponse

from budget.serializers import TransactionSerializer, ChartDataSerializer, BalanceHistorySerializer, BalanceHistoryRefreshSerializer
from budget.models import Transaction, MoneyAccount, BalanceHistory
from budget.summary import create_summary_table, create_yearly_summary
from budget.forms import BudgetExpenseEntryForm


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
        summary, totals = create_yearly_summary(2023)

        serializer = ChartDataSerializer(summary)

        return Response(serializer.data)


class TransactionRemoveAPIView(APIView):
    def delete(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        transaction.delete()
        return Response({"message": "Transaction deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class TransactionUpdateAPIView(APIView):
    def get(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)

    def put(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        serializer = TransactionSerializer(transaction, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Transaction updated successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionFormAPIView(APIView):
    def get(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        form = BudgetExpenseEntryForm(instance=transaction)
        form_html = render_to_string('budget/transaction_form.html', {'form': form})
        return HttpResponse(form_html)


class TransactionCreateAPIView(APIView):
    def delete(self, request, format=None):
        serializer = TransactionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
