from django.db import models
from datetime import datetime, date
from .const import LEVEL_CHOICES

from dashboard.calendar_table import get_month_days
from dashboard.models import UseUser, Certificate, AddOnService,ServiceMaster

class ServiceMonthlyRecord(models.Model):
    '''実際に提供されたサービスの記録を管理するモデル'''

    class Meta:
        verbose_name_plural = "月間提供表"
        unique_together = ('user', 'date')  # その月のサービス提供票は1件のみ

    office = models.ForeignKey('Office', on_delete=models.PROTECT, verbose_name='サービス提供の事業所')
    user = models.ForeignKey(UseUser, on_delete=models.CASCADE, related_name="monthly_records")
    confirmed = models.BooleanField(default=False)  # 確定フラグ
    confirmed_at = models.DateField(verbose_name='確定日', blank=True, null=True)
    date = models.DateField(help_text="月初の日付（例: 2026-07-01）")
    path = models.CharField(max_length=100, blank=True, null=True)  # サービス提供票の格納Path FileFieldに変更するか検討
    weekday_pattern = models.JSONField(default=list)  # 0=月曜日, 6=日曜日
    start_time = models.TimeField(default="09:00")
    end_time = models.TimeField(default="17:00")

    # 単位関連
    total_units = models.IntegerField(verbose_name='総単位数', default=0)  # （限度内＋超過）
    within_units = models.IntegerField(verbose_name='区分支給限度内単位数', default=0)
    over_units = models.IntegerField(verbose_name='限度超過単位数', default=0)

    # 金額関連
    total_cost = models.IntegerField(verbose_name='総費用', default=0)  # （給付対象＋超過分）
    benefit_amount = models.IntegerField(verbose_name='給付費請求額', default=0)  # （国保連に請求する額）
    user_share_amount = models.IntegerField(verbose_name='利用者負担額', default=0)  # （生活保護０,1〜3割＋超過分自己負担）
    public_amount = models.IntegerField(verbose_name='公費請求額', default=0)  # 公費請求額

    # 超過分の内訳
    over_cost = models.IntegerField(verbose_name='限度超過分の総額', default=0)
    over_user_share = models.IntegerField(verbose_name='限度超過分の自己負担額', default=0)

    def __str__(self):
        return f'{self.user} - {self.date.strftime("%Y-%m")}'


class ServicePlan(models.Model):
    class Meta:
        verbose_name_plural = "サービス利用計画"

    user = models.ForeignKey(UseUser, on_delete=models.CASCADE)
    monthly_record = models.ForeignKey(ServiceMonthlyRecord, on_delete=models.CASCADE, related_name="plans", )

    this_year = datetime.now().year
    year = models.IntegerField(choices=[(i, f"{i}年") for i in range(this_year - 1, this_year + 1)], default=this_year)
    month = models.IntegerField(choices=[(i, f"{i}月") for i in range(1, 13)], default=datetime.now().month)

    start_time = models.TimeField(default="09:00")
    end_time = models.TimeField(default="15:00")

    schedule_json = models.JSONField(default=dict, blank=True)
    actual_json = models.JSONField(default=dict, blank=True)

    service_name = models.CharField(max_length=50, null=True, blank=True)
    service_code = models.CharField(max_length=20, null=True, blank=True)
    unit = models.IntegerField(default=0)
    care_level = models.CharField(max_length=10, choices=LEVEL_CHOICES, null=True, blank=True)

    start_day = models.IntegerField(null=True, blank=True, default=1)
    end_day = models.IntegerField(verbose_name="介護認定情報が月の中で変わる時に代わる日を記録", null=True, blank=True)
    cert = models.ForeignKey(Certificate, null=True, blank=True, on_delete=models.PROTECT)

    @property
    def stay_time_category(self):
        delta = datetime.combine(date.min, self.end_time) - datetime.combine(date.min, self.start_time)
        hours = delta.total_seconds() / 3600
        if hours < 3:
            return '<3'
        elif 3 <= hours < 4:
            return '3-4'
        elif 4 <= hours < 5:
            return '4-5'
        elif 5 <= hours < 6:
            return '5-6'
        elif 6 <= hours < 7:
            return '6-7'
        elif 7 <= hours < 8:
            return '7-8'
        elif 8 <= hours < 9:
            return '8-9'
        return None

    @property
    def schedule_dict(self):
        return self.schedule_json or {}  # keyが日付、valueが'1'（サービスあり）か''（なし）

    @property
    def actual_dict(self):
        date = self.actual_json or {}  # keyが日付、valueが{"main": "1" or "", "addon": {加算ID:加算NEME}}
        return {
            str(i): date.get(str(i), {'main': "", 'addon': {}}) for i in range(1, 32)
        }

    def can_edit_day(self, day: int) -> bool:
        """この plan が編集可能な日付かどうか"""
        if self.start_day and day < self.start_day:
            return False
        if self.end_day and day > self.end_day:
            return False
        return True

    def get_total_count(self, row_type) -> int:  # scheduleなら予定の回数、actualなら実績の回数、addonなら全ての加算回数
        if row_type == "schedule":
            date = self.schedule_dict
            return sum(1 for v in date.values() if v == '1')
        elif row_type == "actual":
            date = self.actual_dict
            total = 0
            for key in date.values():
                if key.get("main") == '1':
                    total += 1
            return total
        elif row_type == "addon":  # 全てのaddon
            date = self.actual_dict
            total = 0
            for key in date.values():
                total += len(key.get("addon", []))
            return total

    @property
    def get_addon_summary(self):  # ->{ "加算1": ["1", "5", "12"],"加算2": ["1"] }
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
        return summary  # keyが加算サービス名、valueがその加算が入った日付のリスト

    @property
    def total_actual_units(self):
        date_data = self.actual_dict
        total_units = 0
        # プランに含まれる全加算IDを抽出
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

    def build_schedule(self, weekdays, start_day=1, end_day=None):
        """
        指定された期間内で、該当する曜日に '1' を立てる
        start_day: 開始日 (デフォルト1)
        end_day: 終了日 (Noneなら月末まで)
        """
        import calendar as calendar_module

        # 終了日が指定されていない場合は月末日を取得
        if end_day is None:
            _, end_day = calendar_module.monthrange(self.year, self.month)

        col = get_month_days(self.year, self.month)
        schedule = {}

        for day_info in col:
            d = day_info['day']
            # filler（空データ）は飛ばす
            if not d:
                continue

            # 指定された期間内（start_day ～ end_day）かつ、曜日が一致する場合のみ '1'
            if start_day <= int(d) <= end_day:
                if str(day_info['weekday']) in weekdays:
                    schedule[str(d)] = '1'

        self.schedule_json = schedule

    def apply_service_master(self, target_care_level=None):
        level = target_care_level or self.user.care_level
        service = ServiceMaster.objects.filter(
            care_level=level,
            stay_time_category=self.stay_time_category
        ).first()
        if service:  # 値をコピー
            self.care_level = level
            self.service_name = service.service_name
            self.service_code = service.service_code
            self.unit = service.unit

    def __str__(self):
        return f"{self.user.name} - {self.year}年{self.month}月"