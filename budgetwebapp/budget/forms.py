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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')

        if cleaned_data.get('origin') == 'OUT':
            transaction_type = 'INCOMING'
        elif cleaned_data.get('destination') == 'OUT':
            transaction_type = 'OUTGOING'
        else:
            transaction_type = 'INNER'
        print(transaction_type)
        print(category.transaction_type)
        if transaction_type and category:
            if transaction_type != category.transaction_type:
                raise ValidationError("Transaction type does not match category type")

        return cleaned_data