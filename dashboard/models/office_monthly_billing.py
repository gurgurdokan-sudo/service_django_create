from django.db import models

def kokuhoren_csv_path(office, filename):
    """国保連CSVの保存先パスを生成: uploads/service_sheets_export/事業所ID/年/月/ファイル名"""
    return f"service_sheets_export/{office.office_id}/{office.billing_month.strftime('%Y/%m')}/{filename}"


class OfficeMonthlyBilling(models.Model):
    """事業所 月次請求モデル"""

    # --- 基本情報 ---
    office = models.ForeignKey(
        "Office",
        on_delete=models.CASCADE,
        verbose_name="事業所",
        related_name="monthly_billings",
    )
    billing_month = models.DateField(
        verbose_name="請求年月",
        help_text="該当年月の1日を設定",
    )

    # --- 記録用総金額 ---
    total_amount = models.PositiveBigIntegerField(
        verbose_name="請求合計金額",
        default=0,
        help_text="確定済みの月次記録から集計された金額",
    )

    # --- 国保連CSV ---
    kokuhoren_csv = models.FileField(
        verbose_name="国保連CSVファイル",
        upload_to=kokuhoren_csv_path,
        blank=True,
        null=True,
        help_text="出力された国保連請求CSVのパス",
    )

    # --- CSV発行がされた日 ---
    csv_generated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(verbose_name="更新日時", auto_now=True)

    class Meta:
        verbose_name = "月次請求"
        verbose_name_plural = "月次請求一覧"
        unique_together = ("office", "billing_month")
        ordering = ["-billing_month"]

    def __str__(self):
        return f"{self.office} - {self.billing_month.strftime('%Y年%m月')}請求"

    # --- 表示用プロパティ ---
    @property
    def is_csv_issued(self):
        return bool(self.kokuhoren_csv)