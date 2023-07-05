from django import forms
from django.forms import SelectDateWidget
from .models import Transaction, Category
from django.forms import DateInput


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
