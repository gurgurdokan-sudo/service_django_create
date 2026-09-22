import uuid
from datetime import date
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import login
from django.urls import reverse
from urllib3 import request

from dashboard.models import (
    UseUser, ServiceMonthlyRecord, Office, Municipality, Certificate, ServicePlan, CareManager
)
from dashboard.forms import PlanForm
from dashboard.tests.base import BaseTestCase
from django.test import RequestFactory, TestCase

from dashboard.views.create_plan import create_plan


class CertificateChengeWithPlnaCreateTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # 市町村
        self.municipality = Municipality.objects.create(
            municipality_code=str(uuid.uuid4())[:6],
            prefecture='埼玉県',
            name='新座市',
            area_grade=5
        )
        # 事務所
        self.office = Office.objects.create(
            name='通所介護事務所 民の家',
            office_number=1012175150,
            service_type_code=78,
            municipality=self.municipality,
        )
        # ケアマネ
        self.care_manager = CareManager.objects.create(
            name='ケア マネ',
            office_name='一歩',
            care_management_office_number='1010112032',
        )

        self.user1 = UseUser.objects.create(
            name="テスト利用者",
            name_kana="テスト",
            insured_number=str(uuid.uuid4())[:10],
            date_of_birth=date(1950, 1, 1),
            gender="male",
            care_manager=self.care_manager,
        )
        self.cert1 = Certificate.objects.create(
            user=self.user1,
            insured_number='0190123456',
            care_level='要介護2',
            benefit_rate='0.9',
            limit_start=date(2025, 8, 1),
            limit_end=date(2026, 8, 12),
            is_active=True,
        )

        self.cert2 = Certificate.objects.create(
            user=self.user1,
            insured_number='0190123456',
            care_level='要介護3',
            benefit_rate='0.9',
            limit_start=date(2026, 8, 13),
            limit_end=date(2027, 8, 12),
            is_active=True,
        )

    def test_plan_created_twice_and_record_once(self):
        """
        区分変更がある月に create_plan を POST したとき、
        ServicePlan が 2 行作成され、
        ServiceMonthlyRecord は 1 件だけ作成されることを確認する。
        """
        # POST データ
        post_data = {
            "year": 2026,
            "month": 8,
            "start_time": "09:00",
            "end_time": "15:00",
            "weekdays": ["1", "3", "5"],
        }
        request = self.factory.post(
            reverse("dashboard:createPlan", args=[self.user1.id]),
            data=post_data
        )

        # SessionMiddleware
        session_middleware = SessionMiddleware(lambda request: None)
        session_middleware.process_request(request)
        request.session.save()

        # MessageMiddleware
        messages_middleware = MessageMiddleware(lambda request: None)
        messages_middleware.process_request(request)

        request.user = self.user1
        create_plan(request, self.user1.id)
        # --------------------------------
        # ServiceMonthlyRecord
        # --------------------------------

        records = ServiceMonthlyRecord.objects.filter(
            user=self.user1,
            date=date(2026, 8, 1),
        )

        self.assertEqual(records.count(), 1)

        # --------------------------------
        # ServicePlan
        # --------------------------------

        plans = ServicePlan.objects.filter(
            user=self.user1,
            year=2026,
            month=8,
        )

        self.assertEqual(plans.count(), 2)

        # --------------------------------
        # 認定区分
        # --------------------------------

        p1 = plans.get(care_level="要介護2")
        p2 = plans.get(care_level="要介護3")

        # --------------------------------
        # 適用期間
        # --------------------------------
        print(p1.year,p1.month,p1.end_day)
        print(p2.year,p2.month,p2.start_day)
        self.assertEqual(p1.start_day, 1)
        self.assertEqual(p1.end_day, 12)

        self.assertEqual(p2.start_day, 13)
        self.assertEqual(p2.end_day, 31)

        # --------------------------------
        # Certificate
        # --------------------------------

        self.assertEqual(p1.cert, self.cert1)
        self.assertEqual(p2.cert, self.cert2)

        # --------------------------------
        # ServiceMonthlyRecord
        # --------------------------------

        self.assertEqual(
            p1.monthly_record,
            records.first()
        )

        self.assertEqual(
            p2.monthly_record,
            records.first()
        )

        # --------------------------------
        # Schedule
        # --------------------------------

        self.assertTrue(
            all(
                int(d) <= 12
                for d in p1.schedule_json.keys()
            )
        )

        self.assertTrue(
            all(
                int(d) >= 13
                for d in p2.schedule_json.keys()
            )
        )