from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse

from dashboard.models import (
    User, 
    ServicePlan,
    ServiceMaster,
    ServiceRecord
    )
from dashboard.forms import PlanForm
from dashboard.calendar_table import get_month_days

import logging
logger = logging.getLogger(__name__)

def create_plan(request,user_id):
    if request.method == 'POST':
        form = PlanForm(request.POST,user_id=user_id)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user_id = user_id
            plan.build_schedule(form.cleaned_data['weekdays'])
            plan.apply_service_master() #コピー項目
            plan.save()
            year = request.POST.get('year')
            month = request.POST.get('month')
            messages.success(request,'プランを作成しました')
            date = datetime.date(int(year), int(month), 1)
            try:
                record = ServiceRecord.objects.filter(user=plan.user, date=date).first()
                if not record:
                    week_list = form.cleaned_data['weekdays']
                    logger.info(f'{week_list}でServiceRecordを作成します')
                    record = ServiceRecord(
                        user=plan.user,
                        date=date,
                        weekday_pattern=[int(i) for i in week_list],
                        confirmed=False,
                        start_time=form.cleaned_data['start_time'],
                        end_time=form.cleaned_data['end_time']
                    )
                    record.save()
            except Exception as e:
                logger.error(f"サービス提供票の更新中にエラーが発生しました: {e}")
                raise
            url = reverse('dashboard:service',kwargs={'user_id':user_id})
            return redirect(f'{url}?year={year}&month={month}')
    else:
        user = get_object_or_404(User, id=user_id)
        now = timezone.now()
        year = int(request.GET.get('year',now.year))
        month = int(request.GET.get('month',now.month))
        form = PlanForm({
            'year':year,
            'month':month,
            'start_time':_previous_month_record(user)[0] or '9:00',
            'end_time':_previous_month_record(user)[1] or '17:00'},
            user_id=user_id
            )
        plans = ServicePlan.objects.filter(user = user,year = year,month = month,)
        user_code = plans.values_list("service_code",flat=True) #userチェック済みのサービスコード
        all_plans = list(ServiceMaster.objects #todo関数化
            .exclude(service_code__in = user_code)
            .filter(care_level = user.care_level)
            .values()
        )
        logger.info(f'{year}-{month}です')
        
        context={'year':year,'month':month,'user':user,'form': form,'all_plans':all_plans}
        return render(request,'dashboard/create_plan.html', context )
  
    messages.error(request,f'error')
    return redirect('dashboard:user_list')

def _previous_month_record(user):
    record = ServiceRecord.objects.filter(user=user).order_by('-date').first()
    if record:
        return record.start_time,record.end_time
    return '9:00','17:00'