from datetime import datetime

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework import status, generics

from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend

from budget.serializers import TransactionSerializer, ChartDataSerializer, BalanceHistorySerializer, \
    BalanceHistoryRefreshSerializer
from budget.models import Transaction, Category, MoneyAccount, BalanceHistory
from budget.summary import create_summary_table, create_yearly_summary
from budget.forms import BudgetExpenseEntryForm
from budget.utils import update_request_data_for_transaction
from budget.filters import TransactionFilter


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


#
# class TransactionsAPIView(generics.ListCreateAPIView):
#     queryset = Transaction.objects.select_related('origin', 'destination', 'category').all()
#     serializer_class = TransactionSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_class = TransactionFilter
#
#     def list(self, request, *args, **kwargs):
#         response = super().list(request, *args, **kwargs)
#         serialized_data = response.data
#
#         accounts = {acc.id: str(acc.name) for acc in MoneyAccount.objects.all()}
#         categories = {cat.id: str(cat) for cat in Category.objects.all()}
#
#         # Enrich serialized data with human-readable names
#         for data in serialized_data:
#             data['created_at'] = self.format_timestamp(data['created_at'])
#             data['updated_at'] = self.format_timestamp(data['updated_at'])
#             # data['category'] = categories.get(data['category'], 'Unknown')
#             # data['origin'] = accounts.get(data['origin'], 'Out')
#             # data['destination'] = accounts.get(data['destination'], 'Out')
#
#         return Response(serialized_data)
#
#     @staticmethod
#     def format_timestamp(timestamp_str):
#         from datetime import datetime
#         timestamp = datetime.fromisoformat(timestamp_str[:-1])  # Remove trailing 'Z'
#         return timestamp.strftime('%b %d, %Y %I:%M %p')

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

# class TransactionsAPIView(APIView):
#     def format_timestamp(timestamp_str):
#         timestamp = datetime.fromisoformat(timestamp_str[:-1])  # Remove trailing 'Z'
#         formatted_date = timestamp.strftime('%b %d, %Y %I:%M %p')
#         return formatted_date
#
#     def get(self, request):
#         # transactions = Transaction.objects.all()
#         transactions = Transaction.objects.select_related('origin', 'destination', 'category').all()
#         serializer = TransactionSerializer(transactions, many=True)
#         serialized_data = serializer.data
#
#         # for many transactions,and wanting to reduce DB hits (avoiding N+1 problem):
#         accounts = {acc.id: str(acc.name) for acc in MoneyAccount.objects.all()}
#
#         # todo:
#         # https://stackoverflow.com/questions/9046284/how-i-can-replace-user-id-to-username-in-django-json
#         # https://docs.djangoproject.com/en/dev/topics/serialization/#natural-keys
#         # https://stackoverflow.com/questions/60232446/is-there-a-way-to-retrieve-the-value-of-object-instead-of-its-id
#         # https://www.django-rest-framework.org/api-guide/relations/
#         # Convert timestamp strings into dates
#         for data in serialized_data:
#             data['created_at'] = TransactionsAPIView.format_timestamp(data['created_at'])
#             data['updated_at'] = TransactionsAPIView.format_timestamp(data['updated_at'])
#             data['category'] = str(
#                 Category.objects.get(id=data['category']))  # THIS IS HOW CATEGORY IS DISPLAYED BY NAME, NOT PK
#
#             # todo: this or below or natural keys
#             origin_id = data.get('origin')
#             destination_id = data.get('destination')
#             # data['origin'] = str(MoneyAccount.objects.get(id=origin_id).name) if origin_id else 'Out'
#             # data['destination'] = str(MoneyAccount.objects.get(id=destination_id).name) if destination_id else 'Out'
#             # for many transactions,and wanting to reduce DB hits (avoiding N+1 problem):
#             data['origin'] = accounts.get(origin_id, 'Out')
#             data['destination'] = accounts.get(destination_id, 'Out')
#
#             # todo: this or natural keys
#             # Replace origin and destination IDs with their names
#             # origin_id = data.get('origin')
#             # if origin_id:
#             #     origin_account = MoneyAccount.objects.filter(id=origin_id).first()
#             #     data['origin'] = origin_account.name if origin_account else None
#             # else:
#             #     data['origin'] = None
#             #
#             # destination_id = data.get('destination')
#             # if destination_id:
#             #     destination_account = MoneyAccount.objects.filter(id=destination_id).first()
#             #     data['destination'] = destination_account.name if destination_account else None
#             # else:
#             #     data['destination'] = None
#
#         return Response(serializer.data, status=status.HTTP_200_OK)
#
#     def post(self, request, format=None):
#         serializer = TransactionSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(status=status.HTTP_204_NO_CONTENT)
#
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
