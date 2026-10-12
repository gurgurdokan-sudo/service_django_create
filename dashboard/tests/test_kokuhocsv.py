from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from pathlib import Path

from django.test import TestCase

from dashboard.models import (
    Office,
    UseUser,
    ServiceMonthlyRecord,
    ServicePlan, Municipality, AddOnService, Certificate, CareManager, PublicAssistance,
)
from dashboard.excel.service_calculator import ServiceSheetCalculator
from dashboard.kokuho.builder import ClaimBuilder
from dashboard.kokuho.exporter import CsvExporter


# ==========================
# 期待値の計算（テスト側で独立して持つ）
# ==========================
def rate_units(base_units, rate):
    """率加算の単位数：1単位未満は四捨五入"""
    return int((Decimal(base_units) * Decimal(str(rate))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def yen_down(value, multiplier):
    """金額：1円未満は切り捨て（floatを使わない）"""
    return int((Decimal(value) * Decimal(str(multiplier))).quantize(Decimal('1'), rounding=ROUND_DOWN))


# 7131 の列番号（ClaimBuilder の並びに合わせる）
KIND = 3                 # レコード種別コード '01' / '02' / '10'
D_ITEM_CODE, D_UNIT, D_COUNT, D_SUBTOTAL = 9, 10, 11, 15             # 02 明細
T_LIMIT_UNITS, T_OUT_UNITS, T_INS_UNITS = 11, 12, 15                  # 10 集計
T_PRICE, T_BENEFIT, T_USER_SHARE = 16, 17, 18
T_PUB_UNITS, T_PUB_AMOUNT, T_PUB_SELF = 19, 20, 21


class KokuhoCsvTest(TestCase):

    UNIT_PRICE = '10.45'      # 5級地
    BENEFIT_RATE = '0.9'
    ADDON_RATE = '0.115'      # 現行ソフトCSVの 6107=3174単位（27598×0.115）に合わせる

    def setUp(self):
        # ==========================
        # マスタ 関連
        # ==========================
        self.municipality, _ = Municipality.objects.get_or_create(
            municipality_code='112300',
            defaults={'prefecture': '埼玉県', 'name': '新座市', 'area_grade': 5}
        )
        self.addon: AddOnService = AddOnService.objects.create(
            code="6107",
            type='rate',
            rate=self.ADDON_RATE,
            service_name="通所介護処遇改善加算Ⅱ",
            category="通所介護",
            insurance_type="insurance",
            apply_unit="monthly"
        )
        self.addon2: AddOnService = AddOnService.objects.create(
            code='5301',
            service_name='通所介護入浴介助加算Ⅰ',
            unit=40,
            category='通所介護',
            insurance_type='insurance',
            apply_unit='per_day'
        )
        # actual_json の加算は {AddOnService.id(str): 加算名} の形で保存される
        self.bath = {str(self.addon2.id): self.addon2.service_name}

        self.office_number = 1175101250
        self.office, _ = Office.objects.get_or_create(
            name='通所介護事務所　民の家',
            office_number=self.office_number,
            service_type_code=78,
            municipality=self.municipality,
            default_service=self.addon
        )
        # ==========================
        # ケアマネジャー・利用者
        # ==========================
        self.care_manager2, _ = CareManager.objects.get_or_create(
            name='本多 真人',
            office_name='指定介護事業所 山吹',
            care_management_office_number='1175100625',
        )
        self.user2 = UseUser.objects.create(
            name="生活保護 利用者2",
            name_kana="テスト リヨウシャ2",
            insured_number='0000114983',
            date_of_birth=date(1932, 11, 22),
            gender="female",
            care_manager=self.care_manager2,
        )
        # ==========================
        # 月間提供記録（現行ソフトCSVの値）
        # ==========================
        self.record2, _ = ServiceMonthlyRecord.objects.get_or_create(
            office=self.office,
            user=self.user2,
            date=date(2026, 8, 1),
            defaults={
                'total_units': 30772,
                'service_units': 27598,
                'total_cost': 321567,
                'benefit_amount': 289410,
                'public_amount': 32157,
                'user_share_amount': 0,
                'actual_count': 24,
                'within_units': 30772,
                'over_units': 0,
            }
        )
        # ==========================
        # 生活保護
        # ==========================
        self.hogo = PublicAssistance.objects.create(
            user=self.user2,
            hogo_number='12114617',
            recipient_number='0085902',
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            is_active=True
        )
        # ==========================
        # ServicePlan（入浴介助 5301 は現行CSVと同じ7日分：1〜7日）
        # self.bath は setUp の上で作成
        # ==========================
        self.plan_hogo_1344 = ServicePlan.objects.create(
            user=self.user2, monthly_record=self.record2, year=2026, month=8,
            service_code="1344", care_level="要介護4", unit=1013,
            schedule_json={"1": "1", "2": "1"},
            actual_json={
                "1": {"main": "1", "addon": self.bath},
                "2": {"main": "1", "addon": self.bath},
            },
        )
        self.plan_hogo_1349 = ServicePlan.objects.create(
            user=self.user2, monthly_record=self.record2, year=2026, month=8,
            service_code="1349", care_level="要介護2", unit=1049,
            schedule_json={str(d): "1" for d in range(3, 7)},
            actual_json={str(d): {"main": "1", "addon": self.bath} for d in range(3, 7)},
        )
        self.plan_hogo_1444 = ServicePlan.objects.create(
            user=self.user2, monthly_record=self.record2, year=2026, month=8,
            service_code="1444", care_level="要介護2", unit=1172,
            schedule_json={str(d): "1" for d in range(7, 25)},
            actual_json={
                str(d): {"main": "1", "addon": self.bath if d == 7 else {}}
                for d in range(7, 25)
            },
        )
        self.cert = Certificate.objects.create(
            user=self.user2,
            insured_number="0000114983",
            care_level="要介護4",
            benefit_rate=self.BENEFIT_RATE,
            limit_start=date(2025, 5, 1),
            limit_end=date(2028, 4, 30),
            is_active=True,
        )

    # ---------- ヘルパー ----------
    def _calc(self, plans, office=None):
        return ServiceSheetCalculator({
            'office': office or self.office,
            'user': self.user2,
            'plans': plans,
            'dis_year': 2026,
            'dis_month': 8,
        }).get_results()

    @staticmethod
    def _rows_of(rows, kind):
        return [r for r in rows if r[0] == 2 and str(r[2]) == '7131' and r[KIND] == kind]

    # ==========================
    # 1. 率加算の単位数は四捨五入
    # ==========================
    def test_rate_addon_unit_is_rounded_half_up(self):
        cases = [
            (27598, 3174),   # 3173.77 → 3174（切り捨てだと3173）
            (7720, 888),     # 887.8  → 888
            (3039, 349),     # 349.485 → 349
            (100, 12),       # 11.5   → 12（ちょうど0.5は切り上げ）
            (0, 0),
        ]
        for base, expected in cases:
            with self.subTest(base=base):
                self.assertEqual(self.addon.get_unit(base), expected)
                self.assertEqual(rate_units(base, self.ADDON_RATE), expected)

    # ==========================
    # 2. 月次計算が現行ソフトの金額と一致する
    # ==========================
    def test_monthly_amounts_match_vendor(self):
        res = self._calc(self.record2.plans.all())

        service_units = 2026 + 4196 + 21096 + 40 * 7          # 27598
        def_unit = rate_units(service_units, self.ADDON_RATE)  # 3174
        total_cost = yen_down(service_units + def_unit, self.UNIT_PRICE)   # 30772 × 10.45 = 321567.4 → 321567
        benefit = yen_down(total_cost, self.BENEFIT_RATE)                  # 289410.3 → 289410

        self.assertEqual(res['def_unit'], def_unit)
        self.assertEqual(res['total_cost'], total_cost)
        self.assertEqual(res['total_cost'], 321567)
        self.assertEqual(res['benefit_amount'], benefit)
        self.assertEqual(res['benefit_amount'], 289410)
        self.assertEqual(res['public_amount'], total_cost - benefit)       # 32157
        self.assertEqual(res['user_share_amount'], 0)                      # 生活保護は本人負担なし

    # ==========================
    # 3. 単価計算でfloatの誤差が出ない
    # ==========================
    def test_unit_price_has_no_float_error(self):
        # 180 × 10.45 は 1881 ちょうど。float だと 1880.999... → int() で 1880 になる
        plan = ServicePlan.objects.create(
            user=self.user2, monthly_record=self.record2, year=2026, month=8,
            service_code="1344", care_level="要介護4", unit=180,
            schedule_json={"1": "1"},
            actual_json={"1": {"main": "1", "addon": {}}},
        )
        self.office.default_service = None        # 率加算を外して単価計算だけ見る（保存しない）
        res = self._calc([plan], office=self.office)

        self.assertEqual(res['total_cost'], 1881)
        self.assertEqual(res['benefit_amount'], 1692)      # 1692.9 → 1692
        self.assertEqual(res['public_amount'], 189)

    # ==========================
    # 4. CSV出力と各行の金額の整合性
    # ==========================
    def test_kokuho_csv_is_created(self):
        rows = ClaimBuilder(office=self.office, year=2026, month=8).build()
        self.assertTrue(rows)

        # 1行目（コントロールレコード）
        header = rows[0]
        self.assertEqual(header[0], 1)
        self.assertEqual(str(header[7]), str(self.office.office_number))
        self.assertEqual(header[9], 7)
        self.assertEqual(str(header[10]), "202609")     # 処理対象年月＝提出月（提供月の翌月）

        # 2行目（7111）
        line2 = rows[1]
        self.assertEqual(line2[0], 2)
        self.assertEqual(str(line2[3]), "202608")
        self.assertEqual(str(line2[4]), str(self.office.office_number))

        details = self._rows_of(rows, '02')
        totals = self._rows_of(rows, '10')
        self.assertEqual(len(totals), 1)
        total = totals[0]

        # 02：単位数 × 回数 ＝ サービス単位数
        for r in details:
            with self.subTest(code=r[D_ITEM_CODE]):
                self.assertEqual(int(r[D_UNIT]) * int(r[D_COUNT]), int(r[D_SUBTOTAL]))

        # 02 の合計と 10 の単位数
        rate_row = [r for r in details if str(r[D_ITEM_CODE]) == '6107']
        normal_units = sum(int(r[D_SUBTOTAL]) for r in details if str(r[D_ITEM_CODE]) != '6107')
        self.assertEqual(len(rate_row), 1)
        self.assertEqual(normal_units, 27598)
        self.assertEqual(int(total[T_LIMIT_UNITS]), normal_units)
        self.assertEqual(int(total[T_OUT_UNITS]), rate_units(normal_units, self.ADDON_RATE))   # 3174
        self.assertEqual(int(rate_row[0][D_SUBTOTAL]), int(total[T_OUT_UNITS]))
        self.assertEqual(int(total[T_INS_UNITS]), int(total[T_LIMIT_UNITS]) + int(total[T_OUT_UNITS]))

        # 10：金額の丸め
        ins_units = int(total[T_INS_UNITS])
        total_cost = yen_down(ins_units, self.UNIT_PRICE)
        self.assertEqual(str(total[T_PRICE]), "1045")
        self.assertEqual(int(total[T_BENEFIT]), yen_down(total_cost, self.BENEFIT_RATE))       # 289410
        self.assertEqual(int(total[T_USER_SHARE]), 0)
        self.assertEqual(int(total[T_PUB_UNITS]), ins_units)
        self.assertEqual(int(total[T_PUB_AMOUNT]),
                         total_cost - int(total[T_BENEFIT]) - int(total[T_USER_SHARE]))       # 32157
        self.assertEqual(int(total[T_PUB_SELF]), 0)

        # CSV出力
        csv_path = CsvExporter().export(rows, 2026, 8)
        self.assertTrue(Path(csv_path).exists())
