from dashboard.models import AddOnService
from decimal import Decimal, ROUND_DOWN

class ServiceSheetCalculator:
    def __init__(self, context):
        self.office = context['office']
        self.user = context['user']
        self.plans = context['plans']
        self.add_codes = context.get('add_codes', {})
        self.year = int(context['dis_year'])
        self.month = int(context['dis_month'])
        # self.target_date = date(self.year, self.month, 1)

        cert = self.user.get_certificate(self.year, self.month)
        if not cert: raise ValueError(f"認定情報がありません")

        self.unit_price = float(self.office.unit_price)
        self.benefit_rate = float(cert.benefit_rate) # 0.9など

        # 介護度別の支給限度額
        limits = {'要介護1': 16692, '要介護2': 19705, '要介護3': 27048, '要介護4': 30938, '要介護5': 36217}
        self.max_payment = limits.get(cert.care_level, 0)

        # 生活保護判定
        self.pa_data = self.user.get_public_assistance(self.year, self.month)
        self.is_hogo = self.pa_data is not None

        self.total_act_price_unit = 0
        self.plan_items = []
        self.addon_items = []
        self.schedule_plan_items = []
        self._calculate_base_and_addons()

    def _calculate_base_and_addons(self):
        actual_days = set()

        for plan in self.plans:
            service_code = (
                f"{self.office.service_type_code}{plan.service_code}"
            )
            unit = int(plan.unit)
            count = int(plan.get_total_count("actual"))
            subtotal = unit * count

            # Sheet1用：予定・実績カレンダーはPlan単位で保持する。
            self.schedule_plan_items.append({
                "plan_id": plan.id,
                "name": plan.service_name,
                "code": service_code,
                "unit": unit,
                "start_time": plan.start_time,
                "end_time": plan.end_time,
                "schedule": plan.schedule_dict,
                "actual": plan.actual_dict,
            })

            # 実利用日数は、加算ループの外で集計する。
            for day, info in plan.actual_dict.items():
                if info.get("main") == "1":
                    actual_days.add(str(day))

            # Sheet2用の基本サービス明細。Plan単位の元データを保持する。
            if count > 0:
                self.plan_items.append({
                    "name": plan.service_name,
                    "code": service_code,
                    "unit": unit,
                    "count": count,
                    "subtotal": subtotal,
                })

            self.total_act_price_unit += subtotal

            # 加算はこのPlanに紐づく分だけ処理する。
            for value in plan.get_addon_summary.values():
                addon_obj = value.get("addon")

                if not addon_obj:
                    continue
                if addon_obj.type == "rate":  # 率加算は別で計算
                    continue
                if addon_obj.insurance_type == "self_pay":  # 自費は別で集計
                    continue
                if addon_obj.unit is None:
                    raise ValueError(
                        f"加算単位が設定されていません: {addon_obj.code}"
                    )

                add_count = len(value.get("days", []))
                add_unit = int(addon_obj.unit)
                add_total = add_unit * add_count

                if add_total == 0:  # 0は載せない。減算のマイナスは残す
                    continue

                self.addon_items.append({
                    "id": addon_obj.id,
                    "plan_id": plan.id,
                    "name": addon_obj.service_name,
                    "code": (
                        f"{self.office.service_type_code}{addon_obj.code}"
                    ),
                    "unit": add_unit,
                    "count": add_count,
                    "subtotal": add_total,
                })
                self.total_act_price_unit += add_total

        self.actual_days = len(actual_days)

    def get_results(self):
        # 1. 限度額振り分け
        within_units = min(self.total_act_price_unit, self.max_payment)
        over_units = max(0, self.total_act_price_unit - self.max_payment)

        # 2. デフォルト加算
        def_unit = 0
        if self.office.default_service:
            def_unit = self.office.default_service.get_unit(within_units)
        def_total_cost = _yen(def_unit, self.office.unit_price)

        # 3. 金額算出：単位を合計してから円にする
        total_cost = _yen(within_units + def_unit, self.office.unit_price)
        over_cost = _yen(over_units, self.office.unit_price)

        # 4. 保険請求分
        benefit_amount = _yen(total_cost, self.benefit_rate)
        raw_user_share = total_cost - benefit_amount

        if self.is_hogo:
            # 生活保護：本来の負担分を「公費」へ、本人は「0円」
            public_amount = raw_user_share
            user_share_amount = 0
        else:
            # 一般：公費は「0円」、本人が「負担分」を払う
            public_amount = 0
            user_share_amount = raw_user_share

        return {
            'is_hogo': self.is_hogo,
            'pa_data': self.pa_data,
            'actual_count': self.actual_days, # 日数
            'within_units': within_units,
            'over_units': over_units,
            'total_cost': total_cost,     # 費用合計(10割)
            'benefit_amount': benefit_amount, # 保険請求
            'public_amount': public_amount,       # 公費請求
            'user_share_amount': user_share_amount + over_cost, # 本人支払(超過分込)
            'def_unit': def_unit,
            'def_total_cost': def_total_cost,
            'plan_items': self.plan_items,
            'addon_items': self.addon_items,
            'total_units': self.total_act_price_unit + def_unit,
            'service_units': self.total_act_price_unit,
            "schedule_plan_items": self.schedule_plan_items,
        }

def format_comma(value, default=""):
    """数値をカンマ区切りにする。0やNoneの扱いに対応"""
    try:
        val = int(value)
        if val == 0: return "0"
        return f"{val:,}"
    except (ValueError, TypeError):
        return default


def _yen(value, multiplier):
    """金額：1円未満切り捨て（floatを使わない）"""
    return int((Decimal(value) * Decimal(str(multiplier))).quantize(Decimal('1'), rounding=ROUND_DOWN))