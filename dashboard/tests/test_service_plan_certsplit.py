from datetime import date
import uuid
from django.test import TestCase
from dashboard.models import (
    UseUser, ServiceMonthlyRecord, Office, Municipality, Certificate, ServicePlan
)
from dashboard.forms import PlanForm

class ServicePlanCertSplitTest(TestCase):
    def setUp(self):
        self.user = UseUser.objects.create(
            name="テスト利用者",
            name_kana="テスト",
            insured_number=str(uuid.uuid4())[:10],
            date_of_birth=date(1950, 1, 1),
            gender="male",
        )

        self.record = ServiceMonthlyRecord.objects.create(
            office=Office.objects.create(
                name="事業所",
                office_number=1234567890,
                municipality=Municipality.objects.create(
                    municipality_code=str(uuid.uuid4())[:10],
                    prefecture="埼玉県",
                    name="新座市",
                    area_grade=5,
                ),
                service_type_code=78,
            ),
            user=self.user,
            date=date(2026, 8, 1),
        )

        self.cert1 = Certificate.objects.create(
            user=self.user,
            insured_number=str(uuid.uuid4())[:10],
            care_level="要介護2",
            benefit_rate=1.0,
            limit_start=date(2026, 8, 1),
            limit_end=date(2026, 8, 12),
        )

        self.cert2 = Certificate.objects.create(
            user=self.user,
            insured_number=str(uuid.uuid4())[:10],
            care_level="要介護3",
            benefit_rate=1.0,
            limit_start=date(2026, 8, 13),
            limit_end=date(2026, 8, 31),
        )

    def test_split_cert_creates_two_plans(self):
        form = PlanForm(data={
            "year": 2026,
            "month": 8,
            "start_time": "09:00",
            "end_time": "15:00",
        })

        certs_to_save = [
            {"cert": self.cert1, "start_day": 1, "end_day": 12},
            {"cert": self.cert2, "start_day": 13, "end_day": 31},
        ]

        weekdays = ["1", "3", "5"]  # 月水金

        # 実行
        for item in certs_to_save:
            cert = item["cert"]
            plan = form.save(commit=False)
            plan.pk = None
            plan.user = self.user
            plan.care_level = cert.care_level
            plan.start_day = item["start_day"]
            plan.end_day = item["end_day"]
            plan.monthly_record = self.record
            plan.build_schedule(weekdays, item["start_day"], item["end_day"])
            plan.apply_service_master(cert.care_level)
            plan.cert = cert
            plan.save()

        plans = ServicePlan.objects.filter(user=self.user)

        # 2行作られている
        self.assertEqual(plans.count(), 2)

        p1 = plans.get(care_level="要介護2")
        p2 = plans.get(care_level="要介護3")

        # 認定期間が正しく設定されている
        self.assertEqual(p1.start_day, 1)
        self.assertEqual(p1.end_day, 12)
        self.assertEqual(p2.start_day, 13)
        self.assertEqual(p2.end_day, 31)

        # スケジュールが認定期間内だけ作られている
        self.assertTrue(all(int(d) <= 12 for d in p1.schedule_json.keys()))
        self.assertTrue(all(int(d) >= 13 for d in p2.schedule_json.keys()))
