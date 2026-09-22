from datetime import date
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from dashboard.models import (
    Office,
    UseUser,
    ServiceMonthlyRecord,
    ServicePlan, Municipality, AddOnService,
)
from dashboard.kokuho.builder import ClaimBuilder
from dashboard.kokuho.exporter import CsvExporter


class KokuhoCsvTest(TestCase):

    def setUp(self):
        # ==========================
        # Office 関連
        # ==========================
        # Municipality
        self.municipality = Municipality.objects.create(
            municipality_code = '112300',
            prefecture = '埼玉県',
            name = '新座市',
            area_grade = 5
        )
        self.addon = AddOnService.objects.create(
            code="6107",
            type='rate',
            service_name= "通所介護処遇改善加算Ⅱ",
            category= "通所介護",
            insurance_type= "insurance",
            apply_unit= "monthly"
        )
        print("municipality:", repr(self.municipality), flush=True)
        print("addon:", repr(self.addon), flush=True)
        self.office = Office.objects.create(
            name='通所介護事務所　民の家',
            office_number=1012175150,
            service_type_code=78,
            municipality=self.municipality,
            default_service=self.addon
        )

        # ==========================
        # 利用者
        # ==========================
        self.user1 = UseUser.objects.create(
            name="テスト 利用者1",
            name_kana="テスト リヨウシャ1",
            insured_number="0000000001",
            date_of_birth=date(1950, 1, 1),
            gender="male",
        )

        self.user2 = UseUser.objects.create(
            name="テスト 利用者2",
            name_kana="テスト リヨウシャ2",
            insured_number="0000000002",
            date_of_birth=date(1955, 1, 1),
            gender="female",
        )

        self.user3 = UseUser.objects.create(
            name="テスト 利用者3",
            name_kana="テスト リヨウシャ3",
            insured_number="0000000003",
            date_of_birth=date(1960, 1, 1),
            gender="male",
        )

        # ==========================
        # 月間提供記録
        # ==========================
        self.record1 = ServiceMonthlyRecord.objects.create(
            office=self.office,
            user=self.user1,
            date=date(2026, 8, 1),
        )

        self.record2 = ServiceMonthlyRecord.objects.create(
            office=self.office,
            user=self.user2,
            date=date(2026, 8, 1),
        )

        self.record3 = ServiceMonthlyRecord.objects.create(
            office=self.office,
            user=self.user3,
            date=date(2026, 8, 1),
        )

        # ==========================
        # ServicePlan
        # ==========================
        self.plan1 = ServicePlan.objects.create(
            user=self.user1,
            monthly_record=self.record1,
            year=2026,
            month=8,
            service_code="1348",
            care_level="要介護1",
            schedule_json={
                "1": "1",
                "2": "1",
                "3": "1",
            },
            actual_json={
                "1": {"main": "1", "addon": {}},
                "2": {"main": "1", "addon": {}},
                "3": {"main": "1", "addon": {}},
            },
        )

        self.plan2 = ServicePlan.objects.create(
            user=self.user2,
            monthly_record=self.record2,
            year=2026,
            month=8,
            service_code="1443",
            care_level="要介護2",
            schedule_json={
                "1": "1",
                "5": "1",
            },
            actual_json={
                "1": {"main": "1", "addon": {}},
                "5": {"main": "1", "addon": {}},
            },
        )

        self.plan3 = ServicePlan.objects.create(
            user=self.user3,
            monthly_record=self.record3,
            year=2026,
            month=8,
            service_code="5301",
            care_level="要介護3",
            schedule_json={
                "1": "1",
                "2": "1",
                "3": "1",
                "4": "1",
            },
            actual_json={
                "1": {"main": "1", "addon": {}},
                "2": {"main": "1", "addon": {}},
                "3": {"main": "1", "addon": {}},
                "4": {"main": "1", "addon": {}},
            },
        )

    def test_kokuho_csv_is_created(self):
        builder = ClaimBuilder(
            office=self.office,
            year=2026,
            month=8,
        )

        rows = builder.build()

        self.assertTrue(rows)

        # 1行目
        header = rows[0]

        self.assertEqual(header[0], 1)
        self.assertEqual(str(header[7]), "1012175150")
        self.assertEqual(header[9], 7)
        self.assertEqual(header[10], "202608")

        # CSV出力
        exporter = CsvExporter()

        csv_path = exporter.export(
            rows,
            2026,
            8,
        )
        self.assertTrue(Path(csv_path).exists())

    def exception_test(self):
        office = Office.objects.create(
            name='通所介護事務所　民の家',
            office_number=1012175150,
            service_type_code=81,
            municipality=self.municipality,
            default_service=self.addon
        )
        builder = ClaimBuilder(
            office=self.office,
            year=2026,
            month=8,
        )
        builder = ClaimBuilder(
            office=self.office,
            year=2026,
            month=8,
        )

        rows = builder.build()
