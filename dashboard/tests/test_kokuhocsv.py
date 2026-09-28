from datetime import date
from pathlib import Path

from django.test import TestCase
import uuid

from dashboard.models import (
    Office,
    UseUser,
    ServiceMonthlyRecord,
    ServicePlan, Municipality, AddOnService, Certificate, CareManager, PublicAssistance, ServiceMaster,
)
from dashboard.kokuho.builder import ClaimBuilder
from dashboard.kokuho.exporter import CsvExporter


class KokuhoCsvTest(TestCase):

    def setUp(self):
        # ==========================
        # マスタ 関連
        # ==========================
        self.municipality, _ = Municipality.objects.get_or_create(
            municipality_code='112300',
            defaults={'prefecture': '埼玉県', 'name': '新座市', 'area_grade': 5}
        )
        self.addon:AddOnService = AddOnService.objects.create(
            code="6107",
            type='rate',
            rate='0.09',
            service_name= "通所介護処遇改善加算Ⅱ",
            category= "通所介護",
            insurance_type= "insurance",
            apply_unit= "monthly"
        )
        self.addon2:AddOnService = AddOnService.objects.create(
            code='5301',
            service_name='通所介護入浴介助加算Ⅰ',
            unit=40,
            category='通所介護',
            insurance_type='insurance',
            apply_unit='per_day'
        )

        print("municipality:", repr(self.municipality), flush=True)
        print("addon:", repr(self.addon), flush=True)
        self.office_number = 1175101250
        self.office,_ = Office.objects.get_or_create(
            name='通所介護事務所　民の家',
            office_number=self.office_number,
            service_type_code=78,
            municipality=self.municipality,
            default_service=self.addon
        )
        # ==========================
        # ケアマネジャー
        # ==========================
        # self.care_manager1,_ = CareManager.objects.get_or_create(
        #     name = '田中 一美',
        #     office_name = '住宅支援事業所ケアプラン彩ふく',
        #     care_management_office_number = '1175100518',
        # )
        self.care_manager2,_ = CareManager.objects.get_or_create(
            name='本多 真人',
            office_name='指定介護事業所 山吹',
            care_management_office_number = '0000114983',
        )
        # ==========================
        # 利用者
        # ==========================
        # self.user1 = UseUser.objects.create(
        #     name="テスト 利用者1",
        #     name_kana="テスト リヨウシャ1",
        #     insured_number='0000005553',
        #     date_of_birth=date(1934,11,26),
        #     gender="male",
        #     care_manager= self.care_manager1,
        # )

        self.user2 = UseUser.objects.create(
            name="生活保護 利用者2",
            name_kana="テスト リヨウシャ2",
            insured_number='0000114983',
            date_of_birth=date(1932,11,22),
            gender="female",
            care_manager=self.care_manager2,
        )

        # ==========================
        # 月間提供記録
        # ==========================
        # self.record1 = ServiceMonthlyRecord.objects.create(
        #     office=self.office,
        #     user=self.user1,
        #     date=date(2026, 8, 1),
        #
        #     # 月全体
        #     total_units=8608,
        #     service_units=7720,
        #
        #     # 金額
        #     total_cost=89953,
        #     benefit_amount=80957,
        #     public_amount=0,
        #     user_share_amount=8996,
        #
        #     # その他
        #     actual_count=8,
        #     within_units=8608,
        #     over_units=0,
        # )

        self.record2,_ = ServiceMonthlyRecord.objects.get_or_create(
            office=self.office,
            user=self.user2,
            date=date(2026, 8, 1),
            defaults={
                # 月全体
                'total_units':30772,
                'service_units':27598,

                # 金額
                'total_cost':321567,
                'benefit_amount':289410,
                'public_amount':32157,
                'user_share_amount':0,

                # その他
                'actual_count':24,
                'within_units':30772,
                'over_units':0
            }
        )
        # ==========================
        # 生活保護
        # ==========================
        self.hogo = PublicAssistance.objects.create(
            user=self.user2,
            hogo_number='12114617',
            recipient_number='0085902',
            start_date=date(2026,8,1),
            end_date=date(2026,8,31),
            is_active=True
        )
        # ==========================
        # ServicePlan
        # ==========================
        # self.plan1 = ServicePlan.objects.create(
        #     user=self.user1,
        #     monthly_record=self.record1,
        #     year=2026,
        #     month=8,
        #     service_code="1348",
        #     care_level="要介護3",
        #     unit=925,
        #     schedule_json={
        #         "1": "1",
        #         "2": "1",
        #         "3": "1",
        #     },
        #     actual_json={
        #         "1": {"main": "1", "addon": ["5301"]},
        #         "2": {"main": "1", "addon": ["5301"]},
        #         "3": {"main": "1", "addon": ["5301"]},
        #         "4": {"main": "1", "addon": ["5301"]},
        #         "5": {"main": "1", "addon": ["5301"]},
        #         "6": {"main": "1", "addon": ["5301"]},
        #         "7": {"main": "1", "addon": ["5301"]},
        #         "8": {"main": "1", "addon": ["5301"]},
        #     },
        # )

        self.plan_hogo_1344 = ServicePlan.objects.create(
            user=self.user2,
            monthly_record=self.record2,
            year=2026,
            month=8,
            service_code="1344",
            care_level="要介護4",
            unit=1013,

            schedule_json={
                "1": "1",
                "2": "1",
            },

            actual_json={
                "1": {"main": "1", "addon": ["5301"]},
                "2": {"main": "1", "addon": ["5301"]},
            },
        )
        self.plan_hogo_1349 = ServicePlan.objects.create(
            user=self.user2,
            monthly_record=self.record2,
            year=2026,
            month=8,
            service_code="1349",
            care_level="要介護2",
            unit=1049,
            schedule_json={
                "3": "1",
                "4": "1",
                "5": "1",
                "6": "1",
            },

            actual_json={
                "3": {"main": "1", "addon": ["5301"]},
                "4": {"main": "1", "addon": ["5301"]},
                "5": {"main": "1", "addon": ["5301"]},
                "6": {"main": "1", "addon": ["5301"]},
            },
        )
        self.plan_hogo_1444 = ServicePlan.objects.create(
            user=self.user2,
            monthly_record=self.record2,
            year=2026,
            month=8,
            service_code="1444",
            care_level="要介護2",
            unit=1172,
            schedule_json={
                str(day): "1"
                for day in range(7, 25)
            },

            actual_json={
                str(day): {"main": "1", "addon": ["5301"]}
                for day in range(7, 25)
            },
        )
        self.cerc = Certificate.objects.create(
            user=self.user2,
            insured_number="0000114983",
            care_level="要介護4",
            benefit_rate="0.9",
            limit_start=date(2024, 8, 1),
            limit_end=date(2026, 8, 1),
            is_active=True,
        )

        # ==========================
        # Certificate
        # ==========================
        # self.cert1=Certificate.objects.create(
        #     user=self.user1,
        #     insured_number='0190123456',
        #     care_level = '要介護1',
        #     benefit_rate = '0.9',
        #     limit_start = date(2024, 8, 1),
        #     limit_end = date(2027, 8, 1),
        #     is_active = True,
        #     created_at=date(2024, 8, 1),
        # )
        # self.cert2 = Certificate.objects.create(
        #     user=self.user2,
        #     insured_number='0190123458',
        #     care_level='要介護2',
        #     benefit_rate='0.9',
        #     limit_start=date(2024, 8, 1),
        #     limit_end=date(2026, 8, 1),
        #     is_active=True,
        #     created_at=date(2024, 8, 1),
        # )

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
        self.assertEqual(str(header[7]), str(self.office.office_number))
        self.assertEqual(header[9], 7)
        self.assertEqual(header[10], "202608")

        # 2行目
        line2 = rows[1]
        self.assertEqual(line2[0], 2)
        self.assertEqual(str(line2[3]),"202608" )
        self.assertEqual(str(line2[4]), str(self.office.office_number))
        # user行
        # line_user1 = rows[3]
        # self.assertEqual(line_user1[0], 2)
        # self.assertEqual(str(line_user1[4]),"202608" )
        # self.assertEqual(str(line_user1[5]),str(self.office.office_number) )
        # self.assertEqual(str(line_user1[6]),self.municipality.municipality_code.zfill(8) )
        # self.assertEqual(str(line_user1[7]),self.user1.insured_number )
        # self.assertFalse(line_user1[8])
        #
        # line2_shousai = rows[4]
        # self.assertEqual(line2_shousai[9], self.plan1.service_code)
        # # self.assertNotEqual(line2_shousai[10], 0)

        # CSV出力
        exporter = CsvExporter()

        csv_path = exporter.export(
            rows,
            2026,
            8,
        )
        self.assertTrue(Path(csv_path).exists())

    # def exception_test(self):
    #     office = Office.objects.create(
    #         name='通所介護事務所　民の家',
    #         office_number=1012175150,
    #         service_type_code=81,
    #         municipality=self.municipality,
    #         default_service=self.addon
    #     )
    #     builder = ClaimBuilder(
    #         office=self.office,
    #         year=2026,
    #         month=8,
    #     )
    #     builder = ClaimBuilder(
    #         office=self.office,
    #         year=2026,
    #         month=8,
    #     )
    #
    #     rows = builder.build()
