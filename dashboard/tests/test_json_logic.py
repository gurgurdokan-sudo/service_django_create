from django.test import TestCase
from dashboard.models import ServicePlan, UseUser, ServiceMonthlyRecord, Office, Municipality, Certificate
from datetime import date
import uuid

class ServicePlanCountTest(TestCase):
    def setUp(self):
        self.user = UseUser.objects.create(
            name="テスト ユーザー",
            name_kana="テスト",
            insured_number=str(uuid.uuid4())[:10],
            date_of_birth=date(1950, 1, 1),
            gender="male",
        )

        self.office = Office.objects.create(
            name="事業所",
            office_number=1234567890,
            municipality=Municipality.objects.create(
                municipality_code=str(uuid.uuid4())[:6],
                prefecture="埼玉県",
                name="新座市",
                area_grade=5,
            ),
            service_type_code=78,
        )

        self.record = ServiceMonthlyRecord.objects.create(
            office=self.office,
            user=self.user,
            date=date(2026, 8, 1),
        )

        # テスト対象の actual_json
        self.plan = ServicePlan.objects.create(
            user=self.user,
            monthly_record=self.record,
            year=2026,
            month=8,
            service_code="1348",
            care_level="要介護1",
            actual_json={
                "1": {"main": "1", "addon": {"6107": "処遇改善加算Ⅱ","5301": '通所介護入浴介助加算Ⅰ'}},
                "2": {"main": "",  "addon": {}},
                "3": {"main": "1", "addon": {"6107": "処遇改善加算Ⅱ"}},
            }
        )

    def test_actual_count(self):
        """main='1' の日だけカウントされる"""
        self.assertEqual(self.plan.get_total_count("actual"), 2)

    def test_addon_count(self):
        """addon の dict のキー数をカウントする"""
        self.assertEqual(self.plan.get_total_count("addon"), 3)

    def test_schedule_count(self):
        """schedule_json が空なら 0"""
        self.assertEqual(self.plan.get_total_count("schedule"), 0)
    def test_summary_count(self):
        print(self.plan.get_addon_summary)
        self.assertEqual(self.plan.get_addon_summary, 0)