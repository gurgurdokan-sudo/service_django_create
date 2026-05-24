from django import forms
from .models import User, ServicePlan, Certificate, CareManager

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name','name_kana','insured_number','date_of_birth','gender','benefit_rate','notes']
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
    def __init__(self, *args, **kwargs):
        user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)
        if user_id:
            self.user_id = user_id
        for filde_name in self.fields:
            if not filde_name.startswith('weekdays'):
                self.fields[filde_name].widget.attrs['class']= f'form-control {filde_name}'
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
class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['care_level','benefit_limit_flag', 
        'limit_amount_type', 'limit_start', 'limit_end']
        widgets = {
            'limit_start': forms.DateInput(attrs={'type': 'date'}),
            'limit_end': forms.DateInput(attrs={'type': 'date'}),
        }
    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('limit_start')
        end = cleaned.get('limit_end')

        if not start:
            self.add_error('limit_start', '開始日は必須です')

        if not end:
            self.add_error('limit_end', '終了日は必須です')

        if start and end and start > end:
            self.add_error('limit_end', '終了日は開始日より後の日付を指定してください')

        return cleaned
class CertificateUpdateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['care_level','benefit_rate','benefit_limit_flag','limit_amount_type','limit_amount_value','limit_start','limit_end']
        widgets = {
            'limit_start': forms.DateInput(attrs={'type': 'date'}),
            'limit_end': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for filde_name in self.fields:
            if 'benefit_limit_flag' != filde_name:
                self.fields[filde_name].widget.attrs['class']= f'form-control {filde_name}'

class CareManagerForm(forms.ModelForm):
    class Meta:
        model = CareManager
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for filde_name in self.fields:
            if 'benefit_limit_flag' != filde_name:
                self.fields[filde_name].widget.attrs['class']= f'form-control {filde_name}'