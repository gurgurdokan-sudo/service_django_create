from datetime import date
from dashboard.models import ServiceMonthlyRecord
from dashboard.excel.service_calculator import ServiceSheetCalculator


def build_service_summary(user, year, month, save=True):
    record = (ServiceMonthlyRecord.objects
              .filter(user=user, date=date(year, month, 1))
              .select_related('office').first())
    plans = list(record.plans.all()) if record else []

    summary = {
        'insurance': {'plans': [], 'addons': [], 'rate_addon': None},
        'self_pay': {'items': [], 'total': 0},
        'record': None,
        'error': None,
    }
    if not record:
        return summary

    try:
        res = ServiceSheetCalculator({
            'office': record.office, 'user': user, 'plans': plans,
            'dis_year': year, 'dis_month': month,
        }).get_results()
    except ValueError as e:
        summary['error'] = str(e)
        return summary

    for plan, item in zip(plans, res['plan_items']):
        summary['insurance']['plans'].append({
            'id': plan.id, 'code': item['code'], 'name': item['name'],
            'unit': item['unit'],
            'schedule_count': plan.get_total_count('schedule'),
            'actual_count': item['count'], 'subtotal': item['subtotal'],
        })
    summary['insurance']['addons'] = res['addon_items']

    default = record.office.default_service
    if default:
        summary['insurance']['rate_addon'] = {
            'code': f"{record.office.service_type_code}{default.code}",
            'name': default.service_name, 'rate': str(default.rate),
            'units': res['def_unit'],
        }

    items = _self_pay_items(plans)
    summary['self_pay'] = {'items': items, 'total': sum(i['subtotal'] for i in items)}

    if save:
        apply_results(record, res)
    summary['record'] = record_to_dict(record)
    return summary


def _self_pay_items(plans):
    items = {}
    for plan in plans:
        for value in plan.get_addon_summary.values():
            addon = value['addon']
            if addon.insurance_type != 'self_pay':
                continue
            it = items.setdefault(addon.id, {
                'id': addon.id, 'name': addon.service_name,
                'price': addon.price or 0, 'count': 0,
            })
            it['count'] += len(value.get('days', []))
    for it in items.values():
        it['subtotal'] = it['price'] * it['count']
    return list(items.values())