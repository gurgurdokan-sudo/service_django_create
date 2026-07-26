from django import forms

from dashboard.models import User
from .models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        # choice = User.objects.filter().values_list('name')
        fields = ['date', 'title', 'user', 'mood', 'image', 'body']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'title': forms.TextInput(attrs={'placeholder': '利用者の様子'}),
            'body': forms.Textarea(attrs={'rows': 10, 'placeholder': '今日の利用者の詳細'}),
            'user': forms.Select(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super(EntryForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.all()
        self.fields['user'].required = True
        self.fields['user'].empty_label = "選択してください"