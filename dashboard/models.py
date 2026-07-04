from django.db import models
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, date
from dashboard.calendar_table import get_month_days
LEVEL_CHOICES = [
    # ('要支援1', '要支援1'),
    # ('要支援2', '要支援2'),
    ('要介護1', '要介護1'),
    ('要介護2', '要介護2'),
    ('要介護3', '要介護3'),
    ('要介護4', '要介護4'),
    ('要介護5', '要介護5'),
]
class CareManager(models.Model):
    name = models.CharField(max_length=100, verbose_name='担当者名')
    care_manager_number = models.CharField(max_length=20,verbose_name="居宅介護支援専門員番号", blank=True, null=True) #todo
    office_name = models.CharField(max_length=200, verbose_name='居宅介護支援事業所名')  # 居宅介護支援事業所名
    care_management_office_number = models.CharField(max_length=20,verbose_name="居宅介護支援事業所番号")
    tel = models.CharField(max_length=20, blank=True, null=True)
    fax = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.name}（{self.office_name}）"

class User(models.Model): 
    '''被保険者の情報を管理するモデル'''
    care_manager = models.ForeignKey(CareManager,on_delete=models.SET_NULL,null=True)
    name = models.CharField(max_length=100,verbose_name='被保険者氏名')
    name_kana = models.CharField(max_length=100,verbose_name='フリガナ')
    insured_number = models.CharField(unique=True, max_length=10, verbose_name='被保険者番号')
    date_of_birth = models.DateField(verbose_name='生年月日')
    GENDER_CHOICES = [('male', '男性'),('female', '女性'),]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES,verbose_name='性別')

    BENEFIT_RATE_CHOICES = [(0.9, "給付率90%（1割負担）"),(0.8, "給付率80%（2割負担）"),(0.7, "給付率70%（3割負担）")]
    benefit_rate = models.FloatField(choices=BENEFIT_RATE_CHOICES, verbose_name = '給付率')
    notes = models.TextField(blank=True,default="",verbose_name='メモ')
    def __str__(self):
        return self.name

    @property
    def max_separate_payment(self):
        match self.care_level:
            case '要支援1': return 5003
            case '要支援2': return 10473
            case '要介護1': return 16692
            case '要介護2': return 19705
            case '要介護3': return 27048
            case '要介護4': return 30938
            case '要介護5': return 36217
            case _: return None
    @property
    def care_level(self): #certificateとlimit_endは存在する前提
        today = timezone.now().date()
        cert = (
            self.certificate.filter(limit_end__gte=today).order_by("-limit_end").first()
        )
        return cert.care_level if cert else '認定情報更新が必要'
    @property
    def old_certificate(self): #最後の適用介護認定
        today = timezone.now().date()
        return (self.certificate
            .filter(limit_end__lt=today)
            .order_by("-limit_end")
            .first()
        )
    @property
    def latest_changed_date(self): #紐づく介護の変更日
        today = timezone.now().date()
        cert = (
            self.certificate
            .filter(limit_end__gte=today)
            .order_by("-limit_end")
            .first()
        )
        return cert.care_level_changed_at

class ServiceMaster(models.Model):
    '''提供されるサービスのマスターデータを管理するモデル'''
    care_level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    STAY_TIME_CHOICES = [('<3','3時間以下'),('3-4','3以上-4未満'),('4-5','4以上-5未満'),\
                        ('5-6','5以上-6未満'),('6-7','6以上-7未満'),('7-8','7以上-8未満'),('8-9','8以上-9未満')]
    stay_time_category = models.CharField(max_length=20, choices=STAY_TIME_CHOICES)
    service_code = models.CharField(max_length=20)
    service_name = models.CharField(max_length=20)
    unit = models.IntegerField()  # 409 など
    description = models.CharField(max_length=100,default="2026-03-01")
    def __str__(self):
        return str(self.service_name)
    @classmethod
    def get_quer_plan(cls,level,stay_time_category):
        try:
            plan = cls.objects.filter(care_level = level,stay_time_category = stay_time_category)
        except cls.DoesNotExist:
            return None
        return plan if plan else None

class ServiceRecord(models.Model): 
    '''実際に提供されたサービスの記録を管理するモデル'''
    class Meta:
        unique_together = ('user', 'date') #その月のサービス提供票は1件のみ

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    confirmed = models.BooleanField(default=False) # 確定フラグ
    date = models.DateField(help_text="月初の日付（例: 2026-07-01）")
    path = models.CharField(max_length=100, blank=True, null=True)  # サービス提供票の格納Path FileFieldに変更するか検討
    weekday_pattern = models.JSONField(default=list)  # 0=月曜日, 6=日曜日
    def __str__(self):
        return f'{self.user} - {self.date.strftime("%Y-%m")}'
class ServicePlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    this_year = datetime.now().year
    year = models.IntegerField(choices=[(i, f"{i}年") for i in range(this_year-1, this_year+1)], default=this_year)
    month = models.IntegerField(choices=[(i, f"{i}月") for i in range(1, 13)], default = datetime.now().month)
    start_time = models.TimeField(default="09:00")
    end_time = models.TimeField(default="15:00")

    schedule_json = models.JSONField(default=dict, blank=True)
    actual_json = models.JSONField(default=dict, blank=True)
    service_name = models.CharField(max_length=50,null=True, blank=True)
    service_code = models.CharField(max_length=20,null=True, blank=True)
    unit = models.IntegerField(default=0)
    @property
    def stay_time_category(self):
        delta = datetime.combine(date.min, self.end_time) - datetime.combine(date.min, self.start_time)
        hours = delta.total_seconds() / 3600
        if hours <= 3: return '<3'
        elif 3 < hours <= 4: return '3-4'
        elif 4 < hours <= 5: return '4-5'
        elif 5 < hours <= 6: return '5-6'
        elif 6 < hours <= 7: return '6-7'
        elif 7 < hours <= 8: return '7-8'
        elif 8 < hours <= 9: return '8-9'
        return None
    @property
    def schedule_dict(self):
        return self.schedule_json or {} #keyが日付、valueが'1'（サービスあり）か''（なし）
    @property
    def actual_dict(self): 
        date = self.actual_json or {} #keyが日付、valueが{"main": "1" or "", "addon": {加算ID:加算NEME}}
        return {
            str(i): date.get(str(i), {'main':"",'addon':{}}) for i in range(1, 32)
        }
    def get_total_count(self,row_type)->int: #scheduleなら予定の回数、actualなら実績の回数、addonなら全ての加算回数
        if row_type == "schedule":
            date = self.schedule_dict
            return sum(1 for v in date.values() if v=='1')
        elif row_type == "actual":
            date = self.actual_dict
            total = 0
            for key in date.values():
                if key.get("main") == '1':
                    total += 1
            return total
        elif row_type == "addon":  #全てのaddon
            date = self.actual_dict
            total = 0
            for key in date.values():
                total += len(key.get("addon", []))
            return total
    @property
    def get_addon_summary(self):  #->{ "加算1": ["1", "5", "12"],"加算2": ["1"] }
        date_data = self.actual_dict 
        all_addon_ids = set()
        for day_info in date_data.values():
            all_addon_ids.update(day_info.get("addon", {}))

        # マスタから名前を引くための辞書
        master = {a.id: a.service_name for a in AddOnService.objects.filter(id__in=all_addon_ids)}

        summary = {}
        for day, day_info in date_data.items():
            for addon_id in day_info.get("addon", {}):
                name = master.get(int(addon_id))
                if name:
                    if name not in summary: summary[name] = []
                    summary[name].append(str(day))
        return summary #keyが加算サービス名、valueがその加算が入った日付のリスト

    @property
    def total_actual_units(self):
        date_data = self.actual_dict
        total_units = 0
        #プランに含まれる全加算IDを抽出
        all_addon_ids = set()
        for day_info in date_data.values():
            all_addon_ids.update(day_info.get("addon", []))

        addon_master = {
            a.id: a.unit for a in AddOnService.objects.filter(id__in=all_addon_ids)
        }
        # 日ごとにループ
        for day_info in date_data.values():
            # --- 基本サービス
            if str(day_info.get("main")) == "1":
                # self.unit は ServicePlan 作成時にマスタからコピーされた基本単位数
                total_units += (self.unit or 0)
                # --- 加算サービス
                for addon_id in day_info.get("addon", []):
                    # マスタから単位数を取得して加算
                    total_units += addon_master.get(int(addon_id), 0)
        return total_units

    @property
    def is_addon(self):
        date = self.actual_dict
        for key in date.values():
            if key.get("addon", []):
                return True
        return False
    def build_schedule(self, weekdays):
        col = get_month_days(self.year, self.month)
        json = {}
        for day in col:
            if str(day['weekday']) in weekdays:
                json[str(day['day'])] = '1'
        self.schedule_json = json

    def apply_service_master(self):
        service = ServiceMaster.objects.filter(
            care_level=self.user.care_level,
            stay_time_category=self.stay_time_category
        ).first()
        if service: #値をコピー
            self.service_name = service.service_name
            self.service_code = service.service_code
            self.unit = service.unit
    def __str__(self):
        return f"{self.user.name} - {self.year}年{self.month}月"
class AddOnService(models.Model):
    code = models.CharField(max_length=20)
    type = models.CharField(choices=[("unit", "単位"), ("rate", "率")])
    unit = models.IntegerField( null=True, blank=True) 
    rate = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    service_name = models.CharField(max_length=100)
    price = models.IntegerField(null=True, blank=True) # 単価（1000円 など）
    category = models.CharField(max_length=20)
    is_tax = models.BooleanField(max_length=20,default=False, verbose_name='課税')  # 非課税 / 課税
    insurance_type = models.CharField(max_length=20, verbose_name='保険適用',choices=[
        ("insurance","保険内"),
        ("self_pay","自費")
    ])
    apply_unit = models.CharField(max_length=20, verbose_name='適用種類', choices=[
        ("monthly","月ごと"),
        ("per_day","日ごと"),
        ("per_service","サービスごと")
    ],null=True, blank=True)
    medical_deduction = models.BooleanField(default=False,null=True, blank=True, verbose_name='医療費控除対象') # 医療費控除対象
    def __str__(self):
        return self.service_name+' ('+self.type+')'
class Municipality(models.Model):
    municipality_code = models.CharField(max_length=6, unique=True, verbose_name='保険者番号')  # 112300
    prefecture = models.CharField(max_length=50, blank=True, null=True, verbose_name = '都道府県')
    name = models.CharField(max_length=50, verbose_name = '市区町村')  # 新座市
    area_grade = models.IntegerField(choices=[(i, f"{i}地域") for i in range(1, 8)], verbose_name = '地域区分')

    def __str__(self):
        return f"{self.name}（{self.municipality_code}）"
class Office(models.Model):
    UNIT_PRICE_TABLE = {7: 11.40,6: 10.90,5: 10.45,4: 10.25,3: 10.15,2: 10.10,1: 10.00}

    name = models.CharField(max_length=100)
    office_number = models.IntegerField()
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT)
    default_service = models.ForeignKey(AddOnService, on_delete=models.SET_NULL, null=True, blank=True)
    SERVICE_TYPE_CHOICES = [(78, "地域密着型通所介護"),(79, "通所介護（通常規模）"),(80, "通所介護（大規模Ⅰ）"),(81, "通所介護（大規模Ⅱ）"),]
    service_type_code = models.IntegerField(choices=SERVICE_TYPE_CHOICES,default=78, verbose_name = '種類コード') #種類コード: 78 （地域密着型通所介護）

    @property # 地域区分ごとの単位単価テーブル
    def unit_price(self):
        return self.UNIT_PRICE_TABLE.get(self.municipality.area_grade, 0)  
    def __str__(self):
        return self.name

class Certificate(models.Model):
    """被保険者証の情報を管理するモデル"""
    BENEFIT_RATE_CHOICES = [(0.9, "給付率90%（1割負担）"),(0.8, "給付率80%（2割負担）"),(0.7, "給付率70%（3割負担）"),]
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="certificate",verbose_name="利用者")
    insured_number = models.CharField(max_length=10,verbose_name="被保険者番号（10桁）")
    care_level = models.CharField(max_length=10,choices=LEVEL_CHOICES,verbose_name="要介護状態区分")
    care_level_changed_at = models.DateField(verbose_name="要介護状態区分変更日",null=True,blank=True)
    # todo↑操作Userは選択できない様にする
    benefit_rate = models.FloatField(choices=BENEFIT_RATE_CHOICES,verbose_name="給付率")
    limit_amount_type = models.CharField(default="規定",max_length=10,choices=[("規定", "規定通り"), ("任意", "任意設定")],verbose_name="区分支給限度基準額区分")
    benefit_limit_flag = models.BooleanField(default=False,verbose_name="給付制限")
    limit_amount_value = models.IntegerField(null=True,blank=True,verbose_name="任意設定の限度額") #todo任意対応
    limit_start = models.DateField(verbose_name="限度額適用開始日")
    limit_end = models.DateField(verbose_name="限度額適用終了日")
    @property
    def status(self):
        today = timezone.now().date()
        if today < self.limit_start:
            return "申請中"
        if self.limit_end and today <= self.limit_end:
            return "認定済み"
        return "消去"
    def __str__(self):
        return self.user.name + f'({self.limit_end})'