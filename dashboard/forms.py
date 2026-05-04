from django import forms
from .models import User, ServicePlan

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'
        labels = {
            'name': '氏名',
            'name_kana': 'フリガナ',
            'care_level': '要介護状態区分',
            'insured_number': '被保険者番号',
            'date_of_birth': '生年月日',
            'gender': '性別',
            'notes' : 'メモ',
        }
        widgets = {
        'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
class PlanForm(forms.ModelForm):
    WEEKDAY_CHOICES = [("0", "月"),("1", "火"),("2", "水"),("3", "木"),("4", "金"),("5", "土"),("6", "日"),]

    weekdays = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=WEEKDAY_CHOICES,
        label="通う曜日"
    )
    def __init__(self, *args, user_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user_id:
            self.user_id = user_id
    class Meta:
        model = ServicePlan
        fields = ['year', 'month', 'start_time', 'end_time']
        labels = {
            'year': 'サービス提供開始年',
            'month': 'サービス提供開始月',
            'start_time': '開始時間',
            'end_time': '終了時間',
        }

        widgets = {
        'start_time': forms.TimeInput(attrs={'type': 'time'}),
        'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
