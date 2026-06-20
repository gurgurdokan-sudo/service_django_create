from django import forms
from django.forms.widgets import SelectDateWidget

from .models import User, ServicePlan, Certificate, CareManager

class UserForm(forms.ModelForm):
    required_css_class = 'required'
    label_suffix = ''
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
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name,field in self.fields.items():
            self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'
            if field.required:
                self.fields[field_name].widget.attrs['required'] = True
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name} required'
class PlanForm(forms.ModelForm):
    required_css_class = 'required'
    label_suffix = ''
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
        for field_name in self.fields:
            if not field_name.startswith('weekdays'):
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'
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
    required_css_class = 'required'
    label_suffix = ''
    class Meta:
        model = Certificate
        fields = ['care_level', 'limit_amount_type','benefit_limit_flag', 'limit_start', 'limit_end']
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name,field in self.fields.items():
            if 'benefit_limit_flag' != field_name:
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'
            if field.required:
                self.fields[field_name].widget.attrs['required'] = True
class CertificateUpdateForm(forms.ModelForm):
    required_css_class = 'required'
    label_suffix = ''
    class Meta:
        verbose_name = '介護保険被保険者証'
        model = Certificate
        fields = ['care_level','benefit_rate','benefit_limit_flag','limit_amount_type','limit_amount_value','limit_start','limit_end']
        widgets = {
            'limit_start': forms.DateInput(attrs={'type': 'date'}),
            'limit_end': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name,field in self.fields.items():
            if 'benefit_limit_flag' != field_name:
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'
            if field.required:
                self.fields[field_name].widget.attrs['required'] = True

class CareManagerForm(forms.ModelForm):
    required_css_class = 'required'
    label_suffix = ''
    class Meta:
        model = CareManager
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.required:
                self.fields[field_name].widget.attrs['required'] = True
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name} required'
            else: self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'