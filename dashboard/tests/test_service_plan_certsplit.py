from dashboard.models import (
    UseUser, ServiceMonthlyRecord, Office, Municipality, Certificate, ServicePlan
)
from dashboard.forms import PlanForm
from dashboard.tests.base import BaseTestCase


class ServicePlanCertSplitTest(BaseTestCase):

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
