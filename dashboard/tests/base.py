# dashboard/tests/base.py
from django.test import TestCase
from datetime import date
import uuid

from dashboard.models import (
    UseUser, Office, Municipality,
    AddOnService, ServiceMaster,
    CareManager, Certificate, ServiceMonthlyRecord
)

class BaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):

        # 市町村
        cls.municipality = Municipality.objects.create(
            municipality_code=str(uuid.uuid4())[:6],
            prefecture='埼玉県',
            name='新座市',
            area_grade=5
        )

        # 加算マスタ
        cls.default_addon = AddOnService.objects.create(
            service_name="処遇改善加算Ⅱ",
            unit=888,
            insurance_type="insurance",
        )

        # 事務所
        cls.office = Office.objects.create(
            name='通所介護事務所 民の家',
            office_number=1012175150,
            service_type_code=78,
            municipality=cls.municipality,
            default_service=cls.default_addon
        )

        # ケアマネ
        cls.care_manager = CareManager.objects.create(
            name='ケア マネ',
            office_name='一歩',
            care_management_office_number='1010112032',
        )

        # ==========================
        # 利用者
        # ==========================
        cls.user = UseUser.objects.create(
            name="テスト利用者",
            name_kana="テスト",
            insured_number=str(uuid.uuid4())[:10],
            date_of_birth=date(1950, 1, 1),
            gender="male",
            care_manager=cls.care_manager,
        )

        cls.user2 = UseUser.objects.create(
            name="テスト 利用者2",
            name_kana="テスト リヨウシャ2",
            insured_number="0000000002",
            date_of_birth=date(1955, 1, 1),
            gender="female",
            care_manager=cls.care_manager,
        )

        cls.user3 = UseUser.objects.create(
            name="テスト 利用者3",
            name_kana="テスト リヨウシャ3",
            insured_number="0000000003",
            date_of_birth=date(1960, 1, 1),
            gender="male",
            care_manager=cls.care_manager,
        )

        # 月間提供票
        cls.record = ServiceMonthlyRecord.objects.create(
            office=cls.office,
            user=cls.user,
            date=date(2026, 8, 1),
        )

        cls.cert1 = Certificate.objects.create(
            user=cls.user,
            insured_number='0190123456',
            care_level='要介護2',
            benefit_rate='0.9',
            limit_start=date(2026, 8, 1),
            limit_end=date(2026, 8, 12),
            is_active=True,
        )

        cls.cert2 = Certificate.objects.create(
            user=cls.user,
            insured_number='0190123457',
            care_level='要介護3',
            benefit_rate='0.9',
            limit_start=date(2026, 8, 13),
            limit_end=date(2026, 8, 31),
            is_active=True,
        )
