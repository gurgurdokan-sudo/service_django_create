from datetime import date
from dateutil.relativedelta import relativedelta
from dashboard.models import ServicePlan

import logging
logger = logging.getLogger(__name__)


def build_service_addon_record(user, year, month) -> list[int]:
    """
    ServicePlan.actual_jsonから加算IDを読み取る
    それを次の月に設定する為のactual_patternをreturn
    """
    # まず前月のServicePlanがあるか
    prev_month = date(year, month, 1) - relativedelta(months=1)
    service_json_list = (
        ServicePlan.objects.filter(
            user=user,
            year=prev_month.year,
            month=prev_month.month
        )
        .values_list('actual_json', flat=True)
    )
    # 前月のPlanの実績の加算でsetを作る
    addon_ids = set()
    for actual_json in service_json_list:
        for day_data in (actual_json or {}).values():
            addon_data = (day_data or {}).get('addon',{}) or {}
            if not isinstance(addon_data, dict):
                continue
            for addon_id in addon_data:
                try:
                    addon_ids.add(int(addon_id))
                except (ValueError, TypeError):
                    continue
    return sorted(addon_ids)
