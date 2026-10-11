from datetime import date
import uuid

from django.test import TestCase

from dashboard.calendar_table import get_month_days
from dashboard.views import user_service_view
from dashboard.views.user_service_view import build_user_service_context
from dashboard.models import (
    UseUser, Office, Municipality, CareManager,
    AddOnService, ServiceMaster,
    ServicePlan, ServiceMonthlyRecord, Certificate,
)


class BuildUserServiceContextTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # 市町村
        cls.municipality = Municipality.objects.create(
            municipality_code=str(uuid.uuid4())[:6],
            prefecture="東京都",
            name="練馬区",
            area_grade=5,
        )

        # 加算マスタ（default_service 用：処遇改善加算は率加算）
        cls.default_addon = AddOnService.objects.create(
            code="6107",
            type="rate",
            rate=0.115,
            service_name="処遇改善加算Ⅱ",
            category="処遇改善",
            insurance_type="insurance",
        )

        # 単位数加算（提供票の actual_json に入れる用）
        cls.unit_addon = AddOnService.objects.create(
            code="5301",
            type="unit",
            unit=40,
            service_name="入浴介助加算Ⅰ",
            category="入浴",
            insurance_type="insurance",
        )

        # 事務所：build_user_service_context は id=1 を取得する
        cls.office = Office.objects.create(
            id=1,
            name="テスト事務所",
            office_number=1234567890,
            municipality=cls.municipality,
            service_type_code=78,
            default_service=cls.default_addon,
        )

        # ケアマネ
        cls.care_manager = CareManager.objects.create(
            name="ケア マネ",
            office_name="一歩",
            care_management_office_number="1010112032",
        )

        # 利用者（認定あり）
        cls.user = UseUser.objects.create(
            name="テスト 利用者",
            name_kana="テスト カナ",
            insured_number=str(uuid.uuid4())[:10],
            date_of_birth=date(1950, 1, 1),
            gender="male",
            care_manager=cls.care_manager,
        )
        cls.cert = Certificate.objects.create(
            user=cls.user,
            insured_number=cls.user.insured_number,
            care_level="要介護2",
            benefit_rate=0.9,
            limit_start=date(2025, 8, 1),
            limit_end=date(2027, 8, 31),
        )

        # サービスマスタ（モーダルに出す未選択プラン用）
        cls.master_selected = ServiceMaster.objects.create(
            service_name="通所介護A",
            service_code="1348",
            unit=772,
            care_level="要介護2",
            stay_time_category="6-7",
        )
        cls.master_unselected = ServiceMaster.objects.create(
            service_name="通所介護B",
            service_code="1349",
            unit=900,
            care_level="要介護2",
            stay_time_category="7-8",
        )
        cls.master_other_level = ServiceMaster.objects.create(
            service_name="通所介護C",
            service_code="1448",
            unit=1000,
            care_level="要介護3",
            stay_time_category="6-7",
        )

        # 月間提供票
        cls.record = ServiceMonthlyRecord.objects.create(
            office=cls.office,
            user=cls.user,
            date=date(2026, 8, 1),
            confirmed=True,
        )

        # プラン（1日目に単位数加算あり）
        cls.plan = ServicePlan.objects.create(
            user=cls.user,
            monthly_record=cls.record,
            year=2026,
            month=8,
            service_name="通所介護A",
            service_code="1348",
            unit=772,
            start_time="09:00",
            end_time="14:00",
            actual_json={
                "1": {"main": "1", "addon": {
                    str(cls.unit_addon.id): cls.unit_addon.service_name
                }},
                "2": {"main": "", "addon": {}},
            },
        )

        # 利用者（認定なし・提供票なし）
        cls.user_no_cert = UseUser.objects.create(
            name="認定なし 利用者",
            name_kana="ニンテイナシ",
            insured_number=str(uuid.uuid4())[:10],
            date_of_birth=date(1945, 5, 5),
            gender="female",
            care_manager=cls.care_manager,
        )

    def _context(self, user=None):
        return build_user_service_context(
            user_id=(user or self.user).id, year=2026, month=8
        )

    def test_keys(self):
        context = self._context()
        expected_keys = {
            "office", "default", "user", "plans", "addons",
            "calendar", "dis_year", "dis_month",
            "current_year", "current_month",
            "monthly_record", "public_assistance", "confirmed",
            "year_range", "month_range",
            "addon_service", "service_masters",
        }
        self.assertEqual(set(context.keys()), expected_keys)

    def test_basic_values(self):
        context = self._context()
        now = user_service_view.now

        self.assertEqual(context["office"], self.office)
        self.assertEqual(context["default"], self.default_addon)
        self.assertEqual(context["user"], self.user)
        self.assertEqual(context["calendar"], get_month_days(2026, 8))
        self.assertEqual(context["dis_year"], 2026)
        self.assertEqual(context["dis_month"], 8)
        self.assertEqual(context["current_year"], now.year)
        self.assertEqual(context["current_month"], now.month)
        self.assertEqual(context["year_range"], range(now.year - 1, now.year + 1))
        self.assertEqual(context["month_range"], range(1, 13))
        self.assertIsNone(context["public_assistance"])
        self.assertEqual(
            set(context["addon_service"]),
            {self.default_addon, self.unit_addon},
        )

    def test_plans(self):
        context = self._context()
        self.assertEqual(list(context["plans"]), [self.plan])

    def test_addons(self):
        """get_addon_summary の結果がプランごとにリスト化される"""
        context = self._context()
        self.assertEqual(context["addons"], [{
            "p_id": self.plan.id,
            "id": self.unit_addon.id,
            "name": self.unit_addon.service_name,
            "days": ["1"],
            "total": 1,
        }])

    def test_service_masters(self):
        """選択済み(1348)と別の介護度(要介護3)は除外され、未選択の要介護2だけ残る"""
        context = self._context()
        codes = set(context["service_masters"].values_list("service_code", flat=True))
        self.assertEqual(codes, {"1349"})

    def test_monthly_record_and_confirmed(self):
        context = self._context()
        self.assertEqual(list(context["monthly_record"]), [self.record])
        self.assertTrue(context["confirmed"])

    def test_without_certificate(self):
        """認定がない場合は全マスタを返し、エラーログを出す"""
        with self.assertLogs(user_service_view.logger, level="ERROR"):
            context = self._context(self.user_no_cert)

        self.assertEqual(
            set(context["service_masters"]),
            set(ServiceMaster.objects.all()),
        )
        self.assertEqual(list(context["plans"]), [])
        self.assertEqual(context["addons"], [])

    def test_without_monthly_record(self):
        """提供票がない場合は未確定扱い"""
        with self.assertLogs(user_service_view.logger, level="ERROR"):
            context = self._context(self.user_no_cert)

        self.assertFalse(context["confirmed"])
        self.assertEqual(list(context["monthly_record"]), [])