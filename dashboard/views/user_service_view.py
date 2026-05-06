from django.shortcuts import render,redirect, get_object_or_404
from django.utils import timezone

from dashboard.models import User, ServicePlan, ServiceMaster, AddOnService, Office
from dashboard.calendar_table import get_month_days

def user_service(request,user_id):
    target = get_object_or_404(User,id=user_id)
    year = request.GET.get('year')
    month = request.GET.get('month')
    print(year,month,"が表示される",flush=True)
    now = timezone.now()
    calendar = get_month_days(now.year, now.month)
    year = int(year) if year else now.year
    month = int(month) if month else now.month
    plans = ServicePlan.objects.filter(
        user = target,
        year = year,
        month = month,
        )
        
    user_code = plans.values_list("service_code",flat=True) #userチェック済みのサービスコード
    all_plans = (ServiceMaster.objects
        .exclude(service_code__in = user_code)
        .filter(care_level = target.care_level)
        )

    monthly_addon_totals = {}
    add_codes = {}
    for plan in plans:
        addon_names = plan.get_addon_summary
        addon_units = {a.service_name: a.unit for a in AddOnService.objects.filter(service_name__in=addon_names.keys())}
        for addon_name,days in addon_names.items():
            addon = AddOnService.objects.get(service_name = addon_name)
            add_codes[addon_name] = {"unit": addon.unit, "code": addon.code}
            monthly_addon_totals[addon_name] = monthly_addon_totals.get(addon_name,0) + addon.unit * len(days)
    context = {
        'office': Office.objects.get(id=1), #todoログインユーザー事務所
        'user': target,
        'plans': plans, 
        'service': all_plans, #userの対象全プラン
        'calendar': calendar,
        'year': year,
        'month': month,
        'current_year': now.year,
        'current_month': now.month,
        'year_range': range(now.year - 1, now.year + 1),
        'month_range': range(1, 13),
        'add_codes': add_codes, #excleテスト用
        'addon_service': AddOnService.objects.all(),
        'monthly_addon_totals': monthly_addon_totals, #tableのtotal
    }
    return render(request,'dashboard/user_service.html',context)