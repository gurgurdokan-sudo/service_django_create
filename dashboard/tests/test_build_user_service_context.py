from django.test import TestCase
from datetime import date
import uuid

from dashboard.views.user_service_view import build_user_service_context
from dashboard.models import (
    UseUser, Office, Municipality,
    AddOnService, ServiceMaster,
    ServicePlan, ServiceMonthlyRecord, Certificate
)


class BuildUserServiceContextTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        # 利用者
        cls.user = UseUser.objects.create(
            name="テスト 利用者",
            name_kana="テスト カナ",
            insured_number=str(uuid.uuid4())[:10],
            date_of_birth=date(1950, 1, 1),
            gender="male",
        )
        cls.cert1 = Certificate.objects.create(
            user=cls.user,
            insured_number=str(uuid.uuid4())[:10],
            care_level="要介護2",
            benefit_rate=1.0,
            limit_start=date(2025, 8, 1),
            limit_end=date(2027, 8, 12),
        )
        # 事務所
        cls.municipality = Municipality.objects.create(
            municipality_code=str(uuid.uuid4())[:6],
            prefecture="東京都",
            name="練馬区",
            area_grade=5,
        )

        # 加算マスタ（default_service 用）
        cls.default_addon = AddOnService.objects.create(
            service_name="処遇改善加算Ⅱ",
            unit=888,
            insurance_type="insurance",
        )

        cls.office = Office.objects.create(
            name="テスト事務所",
            office_number=1234567890,
            municipality=cls.municipality,
            service_type_code=78,
            default_service=cls.default_addon,
        )

        # サービスマスタ（未選択プラン用）
        cls.master1 = ServiceMaster.objects.create(
            service_name="通所介護A",
            service_code="1348",
            unit=772,
            care_level="要介護2",
            stay_time_category="6-7",
        )

        cls.master2 = ServiceMaster.objects.create(
            service_name="通所介護B",
            service_code="5301",
            unit=40,
            care_level="要介護2",
            stay_time_category="6-7",
        )

        # 月間提供票
        cls.record = ServiceMonthlyRecord.objects.create(
            office=cls.office,
            user=cls.user,
            date=date(2026, 8, 1),
            confirmed=True,
        )

        # プラン（加算あり）
        cls.plan = ServicePlan.objects.create(
            user=cls.user,
            monthly_record=cls.record,
            year=2026,
            month=8,
            service_name="通所介護A",
            service_code="1348",
            unit=772,
            start_time="09:00",
            end_time = "14:00",
            actual_json={
                "1": {"main": "1", "addon": {
                    str(cls.default_addon.id): cls.default_addon.service_name
                }},
                "2": {"main": "", "addon": {}},
            }
        )

    def test_build_user_service_context(self):
        context = build_user_service_context(
            user_id=self.user.id,
            year=2026,
            month=8
        )

        # --- 基本キーの存在確認 ---
        expected_keys = {
            "office", "default", "user", "plans", "service",
            "calendar", "dis_year", "dis_month",
            "current_year", "current_month",
            "year_range", "month_range",
            "add_codes", "addon_service",
            "monthly_addon_totals", "confirmed"
        }
        self.assertTrue(expected_keys.issubset(context.keys()))

        # --- office / default ---
        self.assertEqual(context["office"], self.office)
        self.assertEqual(context["default"], self.default_addon)

        # --- plans ---
        self.assertEqual(list(context["plans"]), [self.plan])

        # --- add_codes（get_addon_summary の集約） ---
        add_codes = context["add_codes"]
        self.assertIn(self.default_addon.id, add_codes)
        self.assertEqual(add_codes[self.default_addon.id]["days"], ["1"])

        # --- confirmed ---
        self.assertTrue(context["confirmed"])

        # --- service（未選択の ServiceMaster） ---
        # plan.service_code = "1348" なので master2 が残る
        service_codes = set(context["service"].values_list("service_code", flat=True))
        print(list(service_codes)[0])
        self.assertEqual(service_codes, {"5301"})
