from django import forms

from .models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['date', 'title', 'mood', 'image', 'body']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'title': forms.TextInput(attrs={'placeholder': '今日の出来事を一言で'}),
            'body': forms.Textarea(attrs={'rows': 10, 'placeholder': '今日はどんな一日でしたか？'}),
        }
