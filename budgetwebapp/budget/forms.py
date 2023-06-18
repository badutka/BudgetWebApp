from django import forms
from .models import Transaction, Category


class BudgetExpenseEntryForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'category', 'amount', 'origin', 'destination']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
