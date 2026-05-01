from rest_framework import serializers
from django.db.models import Q

from budgetwebapp.budget import models


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
    balance_history = models.BalanceHistory.objects.create(
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
        if not models.MoneyAccount.objects.filter(name=value).exists():
            raise serializers.ValidationError('Invalid money account name')
        return value

    def create(self, validated_data):
        money_account_name = validated_data['money_account_name']
        transactions = models.Transaction.objects.filter(
            Q(origin__name=money_account_name) | Q(destination__name=money_account_name)).reverse()
        account = models.MoneyAccount.objects.get(name=money_account_name)
        balance = account.starting_balance
        models.BalanceHistory.objects.filter(money_account__name=money_account_name).delete()  # !!!!!!!!!!!!!!!!!!!!!

        for transaction in transactions:
            if transaction.origin and transaction.origin.name == money_account_name:
                balance = create_balance_history(transaction, account, balance, -transaction.amount)
            if transaction.destination and transaction.destination.name == money_account_name:
                balance = create_balance_history(transaction, account, balance, transaction.amount)

        return {'message': 'Balance history refreshed successfully'}
    # todo: only delete records that changed, meaning: delete all balance entries above the date, and then do nothing when record already exists and create a new one when it doesn't (for given timestamp)


class BalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BalanceHistory
        fields = '__all__'


class MoneyAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MoneyAccount
        fields = '__all__'


class ParentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ParentCategory
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Category
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Transaction
        fields = '__all__'

    def validate(self, data):
        origin = data.get('origin')
        destination = data.get('destination')
        # origin = data.get('origin', getattr(self.instance, 'origin', None))
        # destination = data.get('destination', getattr(self.instance, 'destination', None))
        if not origin and not destination:
            raise serializers.ValidationError("At least one of origin or destination must be set.")

        if origin and destination and origin == destination:
            raise serializers.ValidationError("Origin and destination cannot be the same.")

        # Automatically determine transaction_type
        if origin and destination:
            transaction_type = 'INNER'
        elif origin and not destination:
            transaction_type = 'OUTGOING'
        elif not origin and destination:
            transaction_type = 'INCOMING'
        else:
            raise serializers.ValidationError("Invalid transaction configuration.")

        category = data.get('category')
        if category and category.transaction_type != transaction_type:
            raise serializers.ValidationError(
                f"Transaction type mismatch: expected {category.transaction_type}, got {transaction_type}")
        return data


class MonthlySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MonthlySummary
        fields = '__all__'


class MonthlyCategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MonthlyCategorySummary
        fields = '__all__'


class MonthlyParentCategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MonthlyParentCategorySummary
        fields = '__all__'
