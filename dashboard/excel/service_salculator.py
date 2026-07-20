import textwrap
from django.utils import timezone

# --- ユーティリティ関数 ---

def to_nengo(y,m,d=1):
    """datetimeオブジェクトを受け取り和暦文字を返す"""
    if (y, m, d) >= (2019, 5, 1):
        era, year = "令和", y - 2018
    elif (y, m, d) >= (1989, 1, 8):
        era, year = "平成", y - 1988
    elif (y, m, d) >= (1926, 12, 25):
        era, year = "昭和", y - 1925
    else:
        era, year = "大正", y - 1911
    
    year_str = "元" if year == 1 else str(year)
    return f"{era}{year_str}年"

def format_comma(value, default=""):
    """数値をカンマ区切りにする。0やNoneの扱いに対応"""
    try:
        val = int(value)
        if val == 0: return "0"
        return f"{val:,}"
    except (ValueError, TypeError):
        return default

# --- 計算ロジッククラス ---

class ServiceSheetCalculator:
    def __init__(self, context):
        self.office = context['office']
        self.user = context['user']
        self.plans = context['plans']
        self.add_codes = context.get('add_codes', {})
        
        self.unit_price = float(self.office.unit_price)
        self.benefit_rate = float(self.user.benefit_rate)
        self.max_payment = int(self.user.max_separate_payment)
        
        # 集計用変数
        self.total_act_price_unit = 0  # 地域密着型通所合計
        self.plan_items = []
        self.addon_items = []
        
        self._calculate_base_and_addons()

    def _calculate_base_and_addons(self):
        # 1. 基本プランの集計
        for plan in self.plans:
            count = int(plan.get_total_count('actual'))
            unit = int(plan.unit)
            subtotal = count * unit
            self.plan_items.append({
                'name': plan.service_name,
                'code': f"{self.office.service_type_code}{plan.service_code}",
                'unit': unit,
                'count': count,
                'subtotal': subtotal
            })
            self.total_act_price_unit += subtotal

        # 2. 加算(add_codes)の集計
        # 元のコードの「if not plan.is_addon: continue」の条件を考慮しつつ集計
        has_addon_plan = any(plan.is_addon for plan in self.plans)
        if has_addon_plan:
            for name, item in self.add_codes.items():
                unit = int(item['unit'])
                count = int(item['count'])
                subtotal = unit * count
                if subtotal > 0:
                    self.addon_items.append({
                        'name': name,
                        'code': f"{self.office.service_type_code}{item['code']}" if str(item['code']) != '0' else '',
                        'unit': unit,
                        'count': count,
                        'subtotal': subtotal
                    })
                    self.total_act_price_unit += subtotal

    def get_results(self):
        # 3. 特定事業所加算（デフォルト加算）の計算
        def_unit = 0
        def_total_cost = 0
        def_benefit = 0
        def_user_share = 0
        
        if self.office.default_service:
            rate = float(self.office.default_service.rate)
            def_unit = int(self.total_act_price_unit * rate)
            def_total_cost = int(def_unit * self.unit_price)
            def_benefit = int(def_total_cost * self.benefit_rate)
            def_user_share = def_total_cost - def_benefit

        # 4. 限度額超過の計算
        if self.total_act_price_unit > self.max_payment:
            over_units = self.total_act_price_unit - self.max_payment
            within_units = self.max_payment
        else:
            over_units = 0
            within_units = self.total_act_price_unit

        # 5. 最終金額合計
        seikyu_taisyu = int(within_units * self.unit_price)
        seikyu_bun = int(seikyu_taisyu * self.benefit_rate)
        hutan = seikyu_taisyu - seikyu_bun
        
        over_full_share = int(over_units * self.unit_price)

        return {
            'plan_items': self.plan_items,
            'addon_items': self.addon_items,
            'subtotal_units': self.total_act_price_unit,
            'within_units': within_units,
            'over_units': over_units,
            'def_unit': def_unit,
            'def_total_cost': def_total_cost,
            'def_benefit': def_benefit,
            'def_user_share': def_user_share,
            'seikyu_taisyu': seikyu_taisyu,
            'seikyu_bun': seikyu_bun,
            'hutan': hutan,
            'over_full_share': over_full_share,
            'total_taisyou': seikyu_taisyu + def_total_cost,
            'total_seikyu': seikyu_bun + def_benefit,
            'total_hutan': hutan + def_user_share
        }