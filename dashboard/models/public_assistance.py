from django.db import models
from dashboard.models import UseUser

class PublicAssistance(models.Model):
    """生活保護情報を管理するモデル"""
    class Meta:
        verbose_name_plural= "生活保護情報"
    user = models.ForeignKey(UseUser, on_delete=models.CASCADE, related_name="public_assistance")
    hogo_number = models.CharField(max_length=8, verbose_name="保護番号", help_text="地区番号 + 世帯番号") # 法別番号25など
    recipient_number = models.CharField(max_length=10, verbose_name="受給者番号")
    start_date = models.DateField(verbose_name="適用開始日")
    end_date = models.DateField(verbose_name="適用終了日")
    is_active = models.BooleanField(default=True, verbose_name="有効フラグ")
    def __str__(self):
        start_month = str(self.start_date).split('-')[1]
        return f"{self.user.name}({self.hogo_number})-{start_month}月分"
