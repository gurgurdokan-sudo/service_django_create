from django.db import models
from .const import LEVEL_CHOICES, STAY_TIME_CHOICES, SERVICE_TYPE_CHOICES, UNIT_PRICE_TABLE, SERVICE_TYPE_CODE


class ServiceMaster(models.Model):
    '''提供されるサービスのマスターデータを管理するモデル'''
    class Meta:
        verbose_name_plural= "利用サービス マスタ"
    care_level = models.CharField(
                                max_length=10,
                                choices=LEVEL_CHOICES,
                                verbose_name = '要介護状態区分'
                            )
    stay_time_category = models.CharField(
                                max_length=20,
                                choices=STAY_TIME_CHOICES,
                                verbose_name='滞在時間区分'
                            )
    service_code = models.CharField(
                                max_length=20,
                                verbose_name='サービスコード'
                            )
    service_name = models.CharField(
                                max_length=20,
                                verbose_name = 'サービス名'
                            )
    unit = models.IntegerField(verbose_name='単位')  # 409 など
    description = models.CharField(
                                max_length=100,
                                default="2026-03-01",
                                verbose_name = 'サービス説明'
                            )
    def __str__(self):
        return str(self.service_name)


class AddOnService(models.Model):
    class Meta:
        verbose_name_plural= "加算マスタ"

    service_type_code =  models.IntegerField(choices=SERVICE_TYPE_CHOICES, blank=True, null=True)
    code = models.CharField(max_length=20)
    type = models.CharField(choices=[("unit", "単位"), ("rate", "率")])
    unit = models.IntegerField( null=True, blank=True)
    rate = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    service_name = models.CharField(max_length=100)
    price = models.IntegerField(null=True, blank=True) # 単価（1000円 など）
    category = models.CharField(max_length=20)
    is_tax = models.BooleanField(default=False, verbose_name='課税')  # 非課税 / 課税
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
    @property
    def rate100(self):
        if self.rate:
            return (self.rate * 100).normalize()
    def full_code(self) ->str:
        return f'{self.service_type_code}{self.code}'

    def __str__(self):
        return self.service_name+' ('+self.type+')'
class Municipality(models.Model):
    class Meta:
        verbose_name_plural= "保険者（地域）マスタ"
    municipality_code = models.CharField(max_length=6, unique=True, verbose_name='保険者番号')  # 112300
    prefecture = models.CharField(max_length=50, blank=True, null=True, verbose_name = '都道府県')
    name = models.CharField(max_length=50, verbose_name = '市区町村')  # 新座市
    area_grade = models.IntegerField(choices=[(i, f"{i}地域") for i in range(1, 8)], verbose_name = '地域区分')

    def __str__(self):
        return f"{self.name}（{self.municipality_code}）"
class Office(models.Model):
    class Meta:
        verbose_name_plural = "事務所マスタ"

    name = models.CharField(max_length=100)
    office_number = models.IntegerField()
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT)
    default_service = models.ForeignKey(AddOnService, on_delete=models.SET_NULL, null=True, blank=True)
    service_type_code = models.IntegerField(
        choices=SERVICE_TYPE_CHOICES,
        default=SERVICE_TYPE_CODE, verbose_name = '種類コード',
        help_text="""地域密着型通所介護 → 78
                    通所介護（通常規模） → 79
                    通所介護（大規模Ⅰ） → 80
                    通所介護（大規模Ⅱ） → 81"""
        ) #種類コード: 78 （地域密着型通所介護）

    # Slack連携設定（事業所ごとにボットを持てるようにする。値は管理サイトから設定）
    _slack_bot_token = models.CharField(
        'Slack Botトークン', max_length=100, blank=True, default='',
        help_text='xoxb- で始まるトークン。出退勤ボタン・日報プロンプトの送信に使用',
    )
    _slack_app_token = models.CharField(
        'Slack Appトークン', max_length=100, blank=True, default='',
        help_text='xapp- で始まるトークン（Socket Mode接続用）',
    )


    @property # 地域区分ごとの単位単価テーブル
    def unit_price(self):
        return UNIT_PRICE_TABLE.get(self.municipality.area_grade, 1)
    @property
    def pref_code(self) -> int: #都道府県コードを事務所番号から切り出し
       return int(str(self.office_number)[:2]) 
   
    def __str__(self):
        return self.name
