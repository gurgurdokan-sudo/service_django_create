from datetime import date
import calendar as calendar_module

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse

from dashboard.models import (
    User, 
    ServicePlan,
    ServiceMaster,
    ServiceMonthlyRecord
    )
from dashboard.forms import PlanForm
from dashboard.calendar_table import get_month_days
from dashboard.utils import BreadcrumbUtil

import logging
logger = logging.getLogger(__name__)

def create_plan(request,user_id):
    user = User.objects.get(id=user_id)

    if request.method == 'POST':
        form = PlanForm(request.POST,user_id=user_id)
        if form.is_valid():
            year = request.POST.get('year')
            month = request.POST.get('month')
            weekdays = form.cleaned_data['weekdays']

            # その月の「区分変更日」があるかチェック
            change_cert = user.certificate.filter(
                limit_start__year=year, 
                limit_start__month=month,
                is_active=True
            ).first()


            # 保存する認定情報のリストを作成
            if change_cert:
                old_cert = user.get_certificate(year, month) # 1日時点の認定
                certs_to_save = [
                    {'cert': old_cert, 'end_day': change_cert.limit_start.day - 1},
                    {'cert': change_cert, 'start_day': change_cert.limit_start.day}
                ]
                logger.info(f"区分変更を検知: {change_cert.limit_start.day}日から変更")
            else:
                current_cert = user.get_certificate(year, month)
                certs_to_save = [{'cert': current_cert}]

            # 認定情報ごとに ServicePlan を作成（1行 or 2行）
            for item in certs_to_save:
                cert = item['cert']
                if not cert: continue

                plan = form.save(commit=False)
                plan.pk = None # ループ内で新規登録
                plan.user = user
                plan.care_level = cert.care_level # どの介護度用の行か保存
                
                # スケジュール生成
                start_day = item.get('start_day', 1)
                # その月の末日を取得
                _, last_day = calendar_module.monthrange(year, month)
                end_day = item.get('end_day', last_day)
                
                plan.build_schedule(weekdays, start_day=start_day, end_day=end_day)

                plan.apply_service_master(target_care_level=cert.care_level)
                plan.save()

            # ServiceMonthlyRecord の作成
            date_obj = date(year, month, 1)
            ServiceMonthlyRecord.objects.get_or_create(
                user=user, 
                date=date_obj,
                defaults={
                    'weekday_pattern': [int(i) for i in weekdays],
                    'start_time': form.cleaned_data['start_time'],
                    'end_time': form.cleaned_data['end_time']
                }
            )
            if len(certs_to_save) > 1:
                messages.success(request, f'サービス提供表の計画を作成しました。\n{change_cert.limit_start.day}日から介護度が変更されます。')
            else:
                messages.success(request, 'サービス提供表の計画を作成しました')
            url = reverse('dashboard:service', args=[user_id])
            return redirect(f'{url}?year={year}&month={month}')
    else: #GETリクエスト
        user = get_object_or_404(User, id=user_id)
        now = timezone.now()
        year = int(request.GET.get('year',now.year))
        month = int(request.GET.get('month',now.month))
        messages.success(request, f'{month}月分の適用曜日と時間を登録してください')
        prev = _previous_record(user)
        form = PlanForm({
            'year':year,
            'month':month,
            'start_time':prev.start_time if prev else '09:00',
            'end_time':prev.end_time if prev else '17:00',
            'weekdays':prev.weekday_pattern if prev else []},
            user_id=user_id
            )
        plans = ServicePlan.objects.filter(user = user,year = year,month = month,)
        user_code = plans.values_list("service_code",flat=True) #userチェック済みのサービスコード
        all_plans = list(ServiceMaster.objects #todo関数化
            .exclude(service_code__in = user_code)
            .filter(care_level = user.care_level)
            .values()
        )
        logger.info(f'{year}-{month}を作成する為のフォームを表示')
        crumbs = [
            (f"{user.name}様 サービス提供表作成{year}-{int(month)-1}", ),
            (f"{user.name}様 サービス提供表計画作成", None)
        ]
        
        context={'year':year,'month':month,'user':user,'form': form,'all_plans':all_plans, 'breadcrumbs': BreadcrumbUtil.create(crumbs)}
        return render(request,'dashboard/create_plan.html', context )
  
    messages.error(request,f'error')
    return redirect('dashboard:user_list')

def _previous_record(user):
    return ServiceMonthlyRecord.objects.filter(user=user).order_by('-date').first()