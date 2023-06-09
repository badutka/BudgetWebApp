from django import forms
from .models import BudgetExpenseEntry, Category


class BudgetExpenseEntryForm(forms.ModelForm):
    class Meta:
        model = BudgetExpenseEntry
        fields = ['date', 'category', 'amount', 'origin', 'destination']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()