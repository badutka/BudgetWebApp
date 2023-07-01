from rest_framework import serializers
from django.db.models import Q

from .models import BalanceHistory, Transaction, MoneyAccount, Category, MainCategory, SubCategory


class ChartDataSerializer(serializers.Serializer):
    # labels = serializers.ListField(child=serializers.CharField())
    # expenses_data = serializers.ListField(child=serializers.FloatField())
    # income_data = serializers.ListField(child=serializers.FloatField())
    # balance_data = serializers.ListField(child=serializers.FloatField())

    # todo: summary, totals = create_yearly_summary(2023) HERE

    def to_representation(self, instance):
        # Perform server-side processing here
        summary = instance

        # Manipulate the data or perform calculations
        expenses = [float(val) for val in summary['monthly_expenses'].values()]
        income = [float(val) for val in summary['monthly_income'].values()]
        balance = [float(val) for val in summary['monthly_ending_balance'].values()]

        # Return the processed data
        return {
            'labels': list(summary['monthly_expenses'].keys()),
            'expenses_data': expenses,
            'income_data': income,
            'balance_data': balance,
        }


def create_balance_history(transaction, account, balance, amount):
    balance_history = BalanceHistory.objects.create(
        money_account=account,
        balance_before=balance,
        balance_after=balance + amount,
        created_at=transaction.created_at,
        budget_entry=transaction
    )

    balance_history.save()

    return balance + amount


class BalanceHistoryRefreshSerializer(serializers.Serializer):
    money_account_name = serializers.CharField()

    def validate_money_account_name(self, value):
        # Perform any validation specific to the money_account_name field
        # For example, you can check if the money account exists in the database
        if not MoneyAccount.objects.filter(name=value).exists():
            raise serializers.ValidationError('Invalid money account name')
        return value

    def create(self, validated_data):
        money_account_name = validated_data['money_account_name']
        transactions = Transaction.objects.filter(Q(origin=money_account_name) | Q(destination=money_account_name)).reverse()
        account = MoneyAccount.objects.get(name=money_account_name)
        balance = account.starting_balance
        BalanceHistory.objects.filter(money_account__name=money_account_name).delete()  # !!!!!!!!!!!!!!!!!!!!!
        for transaction in transactions:
            if transaction.origin == money_account_name:
                balance = create_balance_history(transaction, account, balance, -transaction.amount)
            if transaction.destination == money_account_name:
                balance = create_balance_history(transaction, account, balance, transaction.amount)
        return {'message': 'Balance history refreshed successfully'}
    # todo: only delete records that changed, meaning: delete all balance entries above the date, and then do nothing when record already exists and create a new one when it doesn't (for given timestamp)


class BalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceHistory
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
