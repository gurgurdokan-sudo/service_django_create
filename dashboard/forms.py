from datetime import date

from django import forms
from django.forms.utils import ErrorList
from .models import User, ServicePlan, Certificate, CareManager, Office, PublicAssistance


class UserForm(forms.ModelForm):
    required_css_class = 'required'
    class Meta:
        model = User
        fields = ['name','name_kana','insured_number','date_of_birth','gender','benefit_rate','notes']
        labels = {
            'name': '氏名',
            'name_kana': 'フリガナ',
            'insured_number': '被保険者番号',
            'date_of_birth': '生年月日',
            'gender': '性別',
            'notes' : 'メモ',
        }
        widgets = {
        'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    def clean(self):
        cleaned = super().clean()
        dob = cleaned.get('date_of_birth')
        if not dob:
            self._errors['date_of_birth'] = ErrorList(['生年月日は必須です'])
            
        name = cleaned.get('name')
        name = name.replace('　',' ') if name else ''
        if not name:
            parts = [p for p in name.split() if p]
            if len(parts) != 2:
                self._errors['name'] = ErrorList(['氏名は「姓 半角スペース 名」で入力してください'])

        kana = cleaned.get('name_kana')
        kana = kana.replace('　',' ') if kana else ''
        if not kana:
            parts = [p for p in kana.split() if p]
            if len(parts) != 2:
                self._errors['name_kana'] = ErrorList(['フリガナは「セイ 半角スペース メイ」で入力してください'])

        insured_number = str(cleaned.get('insured_number'))
        if not insured_number or len(insured_number) != 10 or not insured_number.isdigit():
            self._errors['insured_number'] = ErrorList(['被保険者番号は10桁の数字で入力してください'])

        queryset = User.objects.filter(insured_number=insured_number)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            self._errors['insured_number'] = ErrorList(['この被保険者番号は既に登録されています'])

        
        return cleaned
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        label_suffix = ''
        for field_name,field in self.fields.items():
            self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'
            if field.required:
                self.fields[field_name].widget.attrs['required'] = True
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name} required'
class PlanForm(forms.ModelForm):
    required_css_class = 'required'
    WEEKDAY_CHOICES = [("0", "月"),("1", "火"),("2", "水"),("3", "木"),("4", "金"),("5", "土"),("6", "日"),]

    weekdays = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=WEEKDAY_CHOICES,
        label="通う曜日"
    )
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
    def __init__(self, *args, **kwargs):
        user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)
        if user_id:
            self.user_id = user_id
        for field_name in self.fields:
            if not field_name.startswith('weekdays'):
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'
class CertificateForm(forms.ModelForm):
    "  認定情報from "
    required_css_class = 'required'
    class Meta:
        model = Certificate
        fields = ['care_level', 'limit_amount_type', 'public_assistance_flag', 'benefit_limit_flag', 'limit_amount_value', 'limit_start', 'limit_end']
        widgets = {
            'limit_start': forms.DateInput(attrs={'type': 'date'}),
            'limit_end': forms.DateInput(attrs={'type': 'date'}),
        }
    public_assistance_flag = forms.BooleanField(
        label='生活保護受給',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    def clean(self):
        cleaned = super().clean()
        care_level = cleaned.get('care_level')
        limit_amount_type = cleaned.get('limit_amount_type')
        limit_amount_value =cleaned.get('limit_amount_value')
        if care_level is None:
            self._errors['care_level'] = ErrorList(['要介護状態区分は必須です'])
        if limit_amount_type is None:
            self._errors['limit_amount_type'] = ErrorList(['限度額区分は必須です'])
        if limit_amount_value and 1000000> limit_amount_value >0 : #todo　とりあえず可笑しな値をはじく
            self._errors['limit_amount_value'] = ErrorList(['正式な限度額を設定してください'])
        return cleaned
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name,field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = f'form-check-input {field_name}'
            else:
                field.widget.attrs['class']= f'form-control {field_name}'
            if field.required:
                field.widget.attrs['required'] = True
                
class PublicAssistanceForm(forms.ModelForm):
    this_year = date.today().year
    YEAR_CHOICES = [(y, f"{y}年") for y in range(this_year - 1, this_year + 1)]
    MONTH_CHOICES = [(m, f"{m}月") for m in range(1, 13)]
    start_year = forms.ChoiceField(choices=YEAR_CHOICES, label="開始年", initial=this_year)
    start_month = forms.ChoiceField(choices=MONTH_CHOICES, label="開始月", initial=date.today().month)
    class Meta:
        model = PublicAssistance
        fields = [
            'hogo_number',
            'recipient_number',
        ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = f'form-control {field_name}'
            if field.required:
                field.widget.attrs['required'] = True
    def clean(self):
        cleaned = super().clean()
        hogo_num =str(cleaned.get('hogo_number'))
        if len(hogo_num) != 8 or not hogo_num.isdigit:
            self.add_error('hogo_number','保護番号は8桁の数字で入力してください')
        rec_num = str(cleaned.get('recipient_number'))
        if len(rec_num) != 10 or not rec_num.isdigit:
            self.add_error('recipient_number', '受給者番号は10桁の数字で入力してください')
        
class CertificateUpdateForm(forms.ModelForm):
    required_css_class = 'required'
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
    class Meta:
        model = CareManager
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        label_suffix = ''
        for field_name, field in self.fields.items():
            if field.required:
                self.fields[field_name].widget.attrs['required'] = True
                self.fields[field_name].widget.attrs['class']= f'form-control {field_name} required'
            else: self.fields[field_name].widget.attrs['class']= f'form-control {field_name}'
    def clean(self):
        cleaned = super().clean()
        cm_num = str(cleaned.get('care_manager_number'))
        if len(cm_num) != 13 or not cm_num.isdigit():
            self.add_error('care_manager_number', '居宅介護支援専門員番号は13桁の数字で入力してください')
        office_num = str(cleaned.get('care_management_office_number'))
        if len(office_num) != 10 or not office_num.isdigit():
            self.add_error('care_management_office_number', '居宅介護支援事業所番号は10桁の数字で入力してください')


class officeSettigForm(forms.ModelForm):
    required_css_class = 'required'
    class Meta:
        model = Office
        fields = ['_slack_bot_token', '_slack_app_token']