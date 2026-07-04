import textwrap
from django.utils import timezone

# --- ユーティリティ関数 ---

def to_nengo(dt):
    """datetimeオブジェクトを受け取り和暦文字を返す"""
    if not dt: return ""
    y, m, d = dt.year, dt.month, dt.day
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
        
        self.results = self._calculate()

    def _calculate(self):
        # 各プランの単位合計
        plan_items = []
        total_units = 0
        
        for plan in self.plans:
            count = int(plan.get_total_count('actual'))
            subtotal = count * int(plan.unit)
            plan_items.append({
                'name': plan.service_name,
                'code': f"{self.office.service_type_code}{plan.service_code}",
                'unit': plan.unit,
                'count': count,
                'subtotal': subtotal
            })
            total_units += subtotal

        # 加算の計算
        addon_items = []
        for name, item in self.add_codes.items():
            count = int(item['count'])
            unit = int(item['unit'])
            subtotal = count * unit
            if subtotal > 0:
                addon_items.append({
                    'name': name,
                    'code': f"{self.office.service_type_code}{item['code']}" if str(item['code']) != '0' else '',
                    'unit': unit,
                    'count': count,
                    'subtotal': subtotal
                })
                total_units += subtotal

        # 特定事業所加算（default_service）
        default_service_units = 0
        if self.office.default_service:
            rate = float(self.office.default_service.rate)
            default_service_units = int(total_units * rate)

        # 限度額計算
        over_units = max(0, total_units - self.max_payment)
        within_units = min(total_units, self.max_payment)
        
        # 金額計算（保険対象分）
        # ※ default_service 分も保険対象として合算
        target_units = within_units + default_service_units
        total_cost = int(target_units * self.unit_price)
        insurance_benefit = int(total_cost * self.benefit_rate)
        user_share = total_cost - insurance_benefit
        
        # 6. 限度額超過分（全額自己負担）
        over_cost = int(over_units * self.unit_price)

        return {
            'plan_items': plan_items,
            'addon_items': addon_items,
            'total_units': total_units,
            'default_service_units': default_service_units,
            'within_units': within_units,
            'over_units': over_units,
            'total_cost': total_cost,
            'insurance_benefit': insurance_benefit,
            'user_share': user_share,
            'over_cost': over_cost,
            'total_user_payment': user_share + over_cost,
            'benefit_rate': self.benefit_rate,
            'unit_price': self.unit_price,
            'max_payment': self.max_payment,
            
        }