from rest_framework import serializers
from .models import BalanceHistory


class ChartDataSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    expenses_data = serializers.ListField(child=serializers.FloatField())
    income_data = serializers.ListField(child=serializers.FloatField())
    balance_data = serializers.ListField(child=serializers.FloatField())

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


class BalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceHistory
        fields = '__all__'
