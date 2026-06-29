from django.shortcuts import render,redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse

from dashboard.models import User, ServicePlan, ServiceMaster, AddOnService, Office, Certificate
from dashboard.calendar_table import get_month_days
from dashboard.excel.service_sheet import create_service_sheet
now = timezone.now()

def build_user_service_context(user_id, year, month):
    target = get_object_or_404(User,id=user_id)
    office = Office.objects.filter(id=1).first() #todoログインユーザー事務所
    plans = ServicePlan.objects.filter(
        user = target,
        year = year,
        month = month,
        )
    print(f'{year}-{month}のサービス提供票のplansを取得',flush=True)
    user_code = plans.values_list("service_code",flat=True) #userチェック済みのサービスコード
    all_plans = (ServiceMaster.objects
        .exclude(service_code__in = user_code)
        .filter(care_level = target.care_level)
        )

    monthly_addon_totals = {}
    add_codes = {} #todo　Excelではcode=0
    for plan in plans:
        addon_names = plan.get_addon_summary or {}
        addon_units = {a.service_name: a.unit for a in AddOnService.objects.filter(service_name__in=addon_names.keys())}
        for addon_name,days in addon_names.items():
            addon = AddOnService.objects.filter(service_name = addon_name).first()
            add_codes[addon_name] = {"unit": addon.unit, "code": addon.code, "count": len(days), "price":addon.price}
            print(days,flush=True)
            if addon.unit:
                monthly_addon_totals[addon_name] = monthly_addon_totals.get(addon_name,0) + addon.unit * len(days)
    
    return {
        'office': office,
        'user': target,
        'plans': plans, 
        'service': all_plans, #userの対象全プラン
        'calendar': get_month_days(year, month),
        'dis_year': year,
        'dis_month': month,
        'current_year': now.year, #Excel出力の表示用
        'current_month': now.month,
        'year_range': range(now.year - 1, now.year + 1),
        'month_range': range(1, 13),
        'add_codes': add_codes, #excelテスト表示
        'addon_service': AddOnService.objects.exclude(code__in=['6102','6100','6099']),
        'monthly_addon_totals': monthly_addon_totals, #tableのtotal
    }

#main
def user_service(request,user_id):
    dis_year = int(request.GET.get('year', now.year))
    dis_month = int(request.GET.get('month', now.month))
    if _is_future_month_not_plan(user_id,dis_year, dis_month):
        print(f'{dis_year}-{dis_month}は未来の年月です')
        url = reverse('dashboard:createPlan',kwargs= {'user_id':user_id})
        return redirect(
            f'{url}?year={dis_year}&month={dis_month}'
            )
    print(f'{dis_year}-{dis_month}のサービス提供票に遷移',flush=True)
    context = build_user_service_context(user_id=user_id,year=dis_year,month=dis_month)
    return render(request,'dashboard/user_service.html',context)

#prevMonth
def prev_month_plan(request, user_id):
    prev_month = now.month - 1 if now.month > 1 else 12
    year = now.year if prev_month != 12 else now.year - 1
    print(f'prev{year}-{prev_month}のサービス提供票に遷移',flush=True)
    context = build_user_service_context(user_id=user_id,year=year,month=prev_month)
    return render(request,'dashboard/user_service.html',context)

def _is_future_month_not_plan(user_id,year, month):
    now = timezone.now()
    if (year > now.year) or (year == now.year and month >= now.month):
        return not ServicePlan.objects.filter(user_id=user_id, year=year, month=month).exists()
    return False