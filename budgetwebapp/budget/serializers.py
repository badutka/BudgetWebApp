from rest_framework import serializers


class ChartDataSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    expenses_data = serializers.ListField(child=serializers.FloatField())
    income_data = serializers.ListField(child=serializers.FloatField())
    balance_data = serializers.ListField(child=serializers.FloatField())
