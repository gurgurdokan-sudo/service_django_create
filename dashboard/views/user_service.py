from django.shortcuts import render,redirect, get_object_or_404
from django.utils import timezone

from dashboard.models import User, ServicePlan, ServiceMaster, AddOnService
from dashboard.calendar_table import get_month_days

def user_service(request,user_id):
    target = get_object_or_404(User,id=user_id)
    now = timezone.now()
    plans = ServicePlan.objects.filter(
        user = target,
        year = now.year,
        month = now.month
        )
    user_code = plans.values_list("service_code",flat=True)
    all_plans = (ServiceMaster.objects
        .exclude(service_code__in = user_code)
        .filter(care_level = target.care_level)
        )

    calendar = get_month_days(now.year, now.month)
    context = {
        'user': target,
        'plans': plans, 
        'service': all_plans, #userの対象全プラン #userの対象全プラン
        'calendar': calendar,
        'addon_service': AddOnService.objects.all(),
        'year_range': range(now.year - 1, now.year + 1),
        'month_range': range(1, 13),
        'current_year': now.year,
        'current_month': now.month,
    }
    return render(request,'dashboard/user_service.html',context)