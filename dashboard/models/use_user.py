from django.db import models
from django.utils import timezone
from datetime import date

from dashboard.models import (
    Certificate,
    CareManager
)
class UseUser(models.Model):
    '''被保険者の情報を管理するモデル'''

    class Meta:
        verbose_name_plural = "利用者"

    care_manager = models.ForeignKey(CareManager, on_delete=models.SET_NULL, null=True, verbose_name='ケアマネージャー')
    name = models.CharField(max_length=100, verbose_name='被保険者氏名')
    name_kana = models.CharField(max_length=100, verbose_name='フリガナ')
    insured_number = models.CharField(unique=True, max_length=10, verbose_name='被保険者番号')
    date_of_birth = models.DateField(verbose_name='生年月日')
    GENDER_CHOICES = [('male', '男性'), ('female', '女性'), ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name='性別')

    # BENEFIT_RATE_CHOICES = [(0.9, "給付率90%（1割負担）"),(0.8, "給付率80%（2割負担）"),(0.7, "給付率70%（3割負担）")]
    # benefit_rate = models.FloatField(choices=BENEFIT_RATE_CHOICES, verbose_name = '給付率')
    notes = models.TextField(blank=True, default="", verbose_name='メモ')

    def __str__(self):
        return self.name

    def get_public_assistance(self, year, month):
        """ 指定した日付時点で有効な生保データを1件返す """
        target_date = date(year, month, 1)
        return self.public_assistance.filter(
            is_active=True,
            start_date__lte=target_date,
            end_date__gte=target_date
        ).first()

    @property
    def is_active_pa_user(self):
        """ 前月で生保だったか判定する """
        return self.public_assistance.filter(is_active=True).exists()

    @property
    def current_certificate(self):
        """今日時点で有効な認定情報を返す"""
        today = timezone.now().date()
        return self.certificate.filter(
            limit_start__lte=today,
            limit_end__gte=today
        ).first()

    def get_certificate_for_month(self, year, month):
        """サービス提供月に有効な認定情報を返す"""
        target_date = date(year, month, 1)
        return self.certificate.filter(
            limit_start__lte=target_date,
            limit_end__gte=target_date
        ).first()

    @property
    def max_separate_payment(self):
        """ 利用者の区分支給限度基準額を返す。認定情報がない場合はNoneを返す """
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

    @property
    def care_level(self):  # certificateとlimit_endは存在する前提
        cert = self.current_certificate
        return cert.care_level if cert else '認定情報更新が必要'

    @property
    def old_certificate(self):  # 最後の適用介護認定
        today = timezone.now().date()
        return (self.certificate
                .filter(limit_end__lt=today)
                .order_by("-limit_end")
                .first()
                )

    def get_certificate(self, year, month) -> Certificate:
        """ 指定した日付時点で有効な認定データを1件返す """
        target_date = date(int(year), int(month), 1)
        return self.certificate.filter(
            limit_start__lte=target_date,
            limit_end__gte=target_date
        ).first()

    def latest_changed_cert(self, year, month) -> Certificate:  # 紐づく介護認定情報
        return Certificate.objects.filter(
            limit_start__year=year,
            limit_start__month=month,
            is_active=True
        ).first()  # 前提1件