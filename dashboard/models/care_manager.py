from django.db import models


class CareManager(models.Model):
    class Meta:
        verbose_name_plural = "ケアマネジャー"

    name = models.CharField(
                            max_length=100,
                            verbose_name='担当者名'
                        )

    care_manager_number = models.CharField(
                            max_length=13,
                            verbose_name="居宅介護支援専門員番号",
                        )

    office_name = models.CharField(
                            max_length=200,
                            verbose_name='居宅介護支援事業所名'
                        )

    care_management_office_number = models.CharField(
                            max_length=10,
                            verbose_name="居宅介護支援事業所番号"
                        )

    tel = models.CharField(
                            max_length=20,
                            blank=True,
                            null=True
                        )

    fax = models.CharField(
                            max_length=20,
                            blank=True,
                            null=True
                        )

    def __str__(self):
        return f"{self.name}（{self.office_name}）"
