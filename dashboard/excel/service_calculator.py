from datetime import date
from dateutil.relativedelta import relativedelta

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
        self._calculate_base_and_addons()

    def _calculate_base_and_addons(self):
        for plan in self.plans:
            count = int(plan.get_total_count('actual'))
            unit = int(plan.unit)
            subtotal = count * unit
            self.plan_items.append({'name': plan.service_name, 'code': f"{self.office.service_type_code}{plan.service_code}", 'unit': unit, 'count': count, 'subtotal': subtotal})
            self.total_act_price_unit += subtotal
        for name, item in self.add_codes.items():
            unit, count = int(item['unit']), int(item['count'])
            subtotal = unit * count
            if subtotal > 0:
                self.addon_items.append({'name': name, 'code': f"{self.office.service_type_code}{item['code']}" if str(item['code']) != '0' else '', 'unit': unit, 'count': count, 'subtotal': subtotal})
                self.total_act_price_unit += subtotal

    def get_results(self):
        # 1. デフォルト加算計算
        def_unit = 0
        def_total_cost = 0
        if self.office.default_service:
            rate = float(self.office.default_service.rate)
            def_unit = int(self.total_act_price_unit * rate)
            def_total_cost = int(def_unit * self.unit_price)

        # 2. 限度額振り分け
        within_units = min(self.total_act_price_unit, self.max_payment)
        over_units = max(0, self.total_act_price_unit - self.max_payment)

        # 3. 金額算出 (10割分)
        seikyu_taisyu = int(within_units * self.unit_price) + def_total_cost
        over_cost = int(over_units * self.unit_price)

        # 4. 請求の内訳計算 (生保対応)
        # 保険請求分 (9割〜7割)
        insurance_seikyu = int(seikyu_taisyu * self.benefit_rate)
        # 本来の利用者負担分 (1割〜3割)
        raw_user_share = seikyu_taisyu - insurance_seikyu

        if self.is_hogo:
            # 生活保護：本来の負担分を「公費」へ、本人は「0円」
            public_seikyu = raw_user_share
            user_hutan = 0
        else:
            # 一般：公費は「0円」、本人が「負担分」を払う
            public_seikyu = 0
            user_hutan = raw_user_share

        return {
            'is_hogo': self.is_hogo,
            'pa_data': self.pa_data,
            'subtotal_units': self.total_act_price_unit,
            'within_units': within_units,
            'over_units': over_units,
            'seikyu_taisyu': seikyu_taisyu,     # 費用合計(10割)
            'insurance_seikyu': insurance_seikyu, # 保険請求
            'public_seikyu': public_seikyu,       # 公費請求
            'user_hutan': user_hutan + over_cost, # 本人支払(超過分込)
            'def_unit': def_unit,
            'def_total_cost': def_total_cost,
            'plan_items': self.plan_items,
            'addon_items': self.addon_items
        }

def format_comma(value, default=""):
    """数値をカンマ区切りにする。0やNoneの扱いに対応"""
    try:
        val = int(value)
        if val == 0: return "0"
        return f"{val:,}"
    except (ValueError, TypeError):
        return default


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