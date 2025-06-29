from django import forms
from django.forms import SelectDateWidget
from .models import Transaction, Category
from django.forms import DateInput
from django.core.exceptions import ValidationError


class CustomDateInput(DateInput):
    input_type = 'date'

class BudgetExpenseEntryForm(forms.ModelForm):
    date = forms.DateField(widget=CustomDateInput)
    description = forms.CharField(widget=forms.Textarea(), required=False)

    class Meta:
        model = Transaction
        fields = ['date', 'category', 'amount', 'origin', 'destination', 'description']

    def clean(self):
        cleaned_data = super().clean()
        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')
        category = cleaned_data.get('category')

        if not origin and not destination:
            raise ValidationError("At least one of origin or destination must be set[form_clean].")

        if origin and destination and origin == destination:
            raise ValidationError("Origin and destination cannot be the same MoneyAccount[form_clean].")

        if origin and destination:
            transaction_type = 'INNER'
        elif origin and not destination:
            transaction_type = 'OUTGOING'
        elif not origin and destination:
            transaction_type = 'INCOMING'
        else:
            transaction_type = None

        if transaction_type and category and category.transaction_type != transaction_type:
            raise ValidationError(f"Transaction type mismatch: expected {category.transaction_type}, got {transaction_type}")
        print(cleaned_data)
        return cleaned_data