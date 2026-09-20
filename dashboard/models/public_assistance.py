from django.db import models
from django.utils import timezone

class PublicAssistance(models.Model):
    """生活保護情報を管理するモデル"""
    class Meta:
        verbose_name_plural= "生活保護情報"
    user = models.ForeignKey(
                    'UseUser',
                    on_delete=models.CASCADE,
                    related_name="public_assistance",
                    verbose_name="利用者"
                )
    hogo_number = models.CharField(
                    max_length=8,
                    verbose_name="保護番号",
                    help_text="地区番号 + 世帯番号"
                ) # 法別番号25など
    recipient_number = models.CharField(
                    max_length=10,
                    verbose_name="受給者番号"
                )
    start_date = models.DateField(verbose_name="適用開始日")
    end_date = models.DateField(verbose_name="適用終了日")
    is_active = models.BooleanField(
                    default=True,
                    verbose_name="有効フラグ",
                    help_text="生活保護情報が有効かどうかを示すフラグ。無効の場合は、利用者の生活保護情報として扱われません。"
                )
    def __str__(self):
        start_month = str(self.start_date).split('-')[1]
        return f"{self.user.name}({self.hogo_number})-{start_month}月分"
    def is_valid(self):
        """同じ月に有効な生活保護情報が存在するかどうかを判定するメソッド"""
        if not self.is_active:
            return False
        today = timezone.now().date()
        if self.start_date <= today and (self.end_date is None or self.end_date >= today):
            return True
        return False