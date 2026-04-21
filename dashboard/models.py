from django.db import models
from django.db.models import Sum
from datetime import datetime, date

LEVEL_CHOICES = [('要支護1', '要支護1'),('要支護2', '要支護2'),('要介護1', '要介護1'),('要介護2', '要介護2'),('要介護3', '要介護3'),('要介護4', '要介護4'),('要介護5', '要介護5'),]

class User(models.Model): 
    '''被保険者の情報を管理するモデル'''
    name = models.CharField(max_length=100,verbose_name='被保険者氏名')
    name_kana = models.CharField(max_length=100,verbose_name='フリガナ')
    care_level = models.CharField(max_length=10,choices=LEVEL_CHOICES,verbose_name='要介護状態区分')  # 要介護1など
    insured_number = models.CharField(max_length=10, blank=True, default="",verbose_name='被保険者番号')
    date_of_birth = models.DateField(blank=True, null=True,verbose_name='生年月日')
    GENDER_CHOICES = [('male', '男性'),('female', '女性'),]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, default="female",verbose_name='性別')
    notes = models.TextField(blank=True,default="",verbose_name='メモ')
    def __str__(self):
        return self.name
    @property
    def max_separate_payment(self):
        match self.care_level:
            case '要支援1':
                return 5003
            case '要支援2':
                return 10473
            case '要介護1':
                return 16692
            case '要介護2':
                return 19705
            case '要介護3':
                return 27048
            case '要介護4':
                return 30938
            case '要介護5':
                return 36217
            case _:
                return None

class ServiceMaster(models.Model):
    '''提供されるサービスのマスターデータを管理するモデル'''
    care_level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    STAY_TIME_CHOICES = [('<3','3時間以下'),('3-4','3以上-4未満'),('4-5','4以上-5未満'),('5-6','5以上-6未満'),('6-7','6以上-7未満'),('7-8','7以上-8未満'),('8-9','8以上-9未満')]
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    PATTERN_CHOICES = [('day','日ごと'),('week','週ごと'),('month','各週ごと')]
    pattern_type = models.CharField(max_length=10, choices=PATTERN_CHOICES)
    pattern_json = models.JSONField(default=dict)
    def __str__(self):
        return str(self.user)
class ServicePlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    this_year = datetime.now().year
    year = models.IntegerField(choices=[(i, f"{i}年") for i in range(this_year-1, this_year+1)], default=this_year)
    month = models.IntegerField(choices=[(i, f"{i}月") for i in range(1, 13)], default = datetime.now().month)
    start_time = models.TimeField(default="09:00")
    end_time = models.TimeField(default="15:00")

    schedule_json = models.JSONField(default=dict, blank=True)
    actual_json = models.JSONField(default=dict, blank=True)
    # ここを追加
    service_name = models.CharField(max_length=50,null=True, blank=True)
    service_code = models.CharField(max_length=20,null=True, blank=True)
    unit = models.IntegerField(null=True, blank=True)
    @property
    def stay_time_category(self):
        delta = datetime.combine(date.min, self.end_time) - datetime.combine(date.min, self.start_time)
        hours = delta.total_seconds() / 3600
        if hours <= 3:
            return '<3'
        elif 3 < hours <= 4:
            return '3-4'
        elif 4 < hours <= 5:
            return '4-5'
        elif 5 < hours <= 6:
            return '5-6'
        elif 6 < hours <= 7:
            return '6-7'
        elif 7 < hours <= 8:
            return '7-8'
        elif 8 < hours <= 9:
            return '8-9'
        return None
    @property
    def schedule_dict(self):
        return self.schedule_json or {}
    @property
    def actual_dict(self):
        date = self.actual_json or {}
        return {
            str(i): date.get(str(i), {'main':"",'addon':[]}) for i in range(1, 32)
        }
    def get_total_count(self,row_type):
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
        elif row_type == "addon":
            date = self.actual_dict
            total = 0
            for key in date.values():
                total += len(key.get("addon", []))
            return total
    @property
    def get_addon_summary(self):
        date_data = self.actual_dict
        all_addon_ids = set()
        for day_info in date_data.values():
            all_addon_ids.update(day_info.get("addon", []))

        # マスタから名前を引くための辞書
        master = {a.id: a.service_name for a in AddOnService.objects.filter(id__in=all_addon_ids)}

        summary = {}
        for day, day_info in date_data.items():
            for addon_id in day_info.get("addon", []):
                name = master.get(int(addon_id))
                if name:
                    if name not in summary: summary[name] = []
                    summary[name].append(str(day))
        return summary

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
            if day_info.get("main") == "1":
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
    def __str__(self):
        return f"{self.user.name} - {self.year}年{self.month}月"
class AddOnService(models.Model):
    code = models.CharField(max_length=20)
    service_name = models.CharField(max_length=100)
    price = models.IntegerField(null=True, blank=True) # 単価（1000円 など）
    unit = models.IntegerField() #無いとエラーになる
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
        return self.service_name
class UserAddOnService(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    addon = models.ForeignKey(AddOnService, on_delete=models.CASCADE)
