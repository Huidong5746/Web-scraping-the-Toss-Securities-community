from django import forms


class StockSearchForm(forms.Form):
    company_name = forms.CharField(
        label="회사명",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "placeholder": "예: 삼성, 카카오, 네이버",
                "autocomplete": "off",
            }
        ),
    )
