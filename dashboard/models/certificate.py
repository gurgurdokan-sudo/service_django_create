from django.db import models
from django.utils import timezone
from .const import LEVEL_CHOICES, BENEFIT_RATE_CHOICES

class Certificate(models.Model):
    """被保険者証の情報を管理するモデル"""
    class Meta:
        verbose_name_plural = "介護認定情報"
        ordering = ['-limit_start', '-created_at']

    user = models.ForeignKey('UseUser' ,
                             on_delete=models.CASCADE ,
                             related_name="certificates" ,
                             verbose_name="利用者"
                         )
    insured_number = models.CharField(
                            max_length=10 ,
                            verbose_name="被保険者番号（10桁）"
                        )
    care_level = models.CharField(
                            max_length=10 ,
                            choices=LEVEL_CHOICES ,
                            verbose_name="要介護状態区分"
                        )
    care_level_changed_at = models.DateField(
                            verbose_name="要介護状態区分変更日" ,
                            null=True ,
                            blank=True
                        )
    benefit_rate = models.FloatField(
                            choices=BENEFIT_RATE_CHOICES ,
                            verbose_name="給付率"
                        )
    limit_amount_type = models.CharField(
                            default="規定" ,
                            max_length=10,
                            choices=[("規定", "規定通り"), ("任意", "任意設定")],
                            verbose_name="区分支給限度基準額区分"
                        )
    benefit_limit_flag = models.BooleanField(
                            default=False ,
                            verbose_name="給付制限"
                        )
    limit_amount_value = models.IntegerField(
                            verbose_name="任意設定の限度額",
                            null=True,
                            blank=True
                        )
    limit_start = models.DateField(verbose_name="限度額適用開始日")
    limit_end = models.DateField(verbose_name="限度額適用終了日")
    is_active = models.BooleanField(
                            default=True,
                            verbose_name="有効フラグ"
                        )
    created_at = models.DateTimeField(
                            auto_now_add=True ,
                            verbose_name="作成日時"
                        )

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
