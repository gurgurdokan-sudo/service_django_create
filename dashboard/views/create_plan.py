from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from dashboard.models import User, ServicePlan, ServiceMaster
from dashboard.forms import PlanForm
from dashboard.calendar_table import get_month_days

def create_plan(request,user_id):
    if request.method == 'POST':
        form = PlanForm(request.POST,user_id=user_id)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user_id = user_id
            stay_cat = plan.stay_time_category
            service_sq = ServiceMaster.objects.filter(
                care_level = plan.user.care_level,
                stay_time_category = stay_cat
            )
            service = service_sq.first() if service_sq else None
            weekdays = form.cleaned_data.get('weekdays', [])
            year = form.cleaned_data['year']
            month = form.cleaned_data['month']
            json = {}
            col = get_month_days(year, month)
            for day in col:
                if str(day['weekday']) in weekdays:
                    json[str(day['day'])] = '1'
            if service:
                plan.service_name = service.service_name
                plan.service_code = service.service_code
                plan.unit = service.unit
                plan.schedule_json = json
            form.save()
            messages.success(request,'プランを作成しました')
            return redirect('dashboard:service',user_id=user_id)
    else:
        user = get_object_or_404(User, id= user_id)
        form = PlanForm(user_id=user_id)
    return render(request,'dashboard/create_plan.html', {
        'form': form,
        'user':user
        })
