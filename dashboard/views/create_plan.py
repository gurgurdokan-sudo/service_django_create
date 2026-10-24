from datetime import date
import calendar as calendar_module

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse

from dashboard.models import (
    UseUser,
    ServicePlan,
    ServiceMaster,
    ServiceMonthlyRecord,
    Office,
    )
from dashboard.forms import PlanForm
from dashboard.utils import BreadcrumbUtil

import logging
logger = logging.getLogger(__name__)

def create_plan(request,user_id):
    user = get_object_or_404(UseUser, pk=user_id)
    try:
        year = int(request.POST.get('year') or request.GET.get('year'))
        month = int(request.POST.get('month') or request.GET.get('month'))
    except (TypeError, ValueError):
        year, month = date.today().year, date.today().month
    from_list =request.GET.get('from_list') or request.POST.get('from_list') # 一覧からの遷移
    if from_list != "0":
        crumbs = [(f"{user.name}様 サービス提供表計画作成", None)]
    else:
        crumbs = [
            (f"{user.name}様 サービス提供表作成画面(今月)",'dashboard:service',[user_id]),
            (f"{user.name}様 サービス提供表作成画面{year}年 {month:02}月", None)
        ]
    form = PlanForm(
                    request.POST if request.method == 'POST' else None,
                    user_id=user_id
                    )
    if request.method=='POST' and form.is_valid():
        weekdays = form.cleaned_data['weekdays']

        try:
            with transaction.atomic():
                # その月の「区分変更日」があるかチェック
                change_cert = user.latest_changed_cert(year, month)
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
                    certs_to_save = [{'cert': current_cert, 'start_day':1}]

                # ServiceMonthlyRecord の作成
                record = ServiceMonthlyRecord.objects.get_or_create(
                    user=user,
                    office=Office.objects.get(id=1), #todo: 事業所を選択できるようにする
                    date=date(year, month, 1),
                    defaults={
                        'weekday_pattern': [int(i) for i in weekdays],
                        'start_time': form.cleaned_data['start_time'],
                        'end_time': form.cleaned_data['end_time']
                    }
                )

                # 認定情報ごとに ServicePlan を作成（1行 or 2行）
                for item in certs_to_save:
                    cert = item['cert']
                    if cert is None: continue

                    plan = form.save(commit=False)
                    plan.pk = None # ループ内で新規登録
                    plan.user = user
                    plan.care_level = cert.care_level # どの介護度用の行か保存

                    # スケジュール生成
                    start_day = item.get('start_day', 1)
                    # その月の末日を取得
                    _, last_day = calendar_module.monthrange(year, month)
                    plan.end_day = item.get('end_day', last_day)

                    # 初期のスケジュールを前回データの週で作成
                    plan.build_schedule(weekdays, start_day=plan.start_day, end_day=plan.end_day)

                    plan.cert =  item.get('cert', certs_to_save[0])
                    plan.apply_service_master(target_care_level=cert.care_level)
                    plan.monthly_record = record[0]  # ServiceMonthlyRecord を関連付け
                    plan.save()


                if change_cert: # 介護適用が変更月
                    messages.success(
                        request,
                        f'サービス提供表の計画を作成しました。'
                        f'{change_cert.limit_start.day}日から介護度が変更されます。'
                    )
                else:
                    messages.success(request, 'サービス提供表の計画を作成しました')
                url = reverse('dashboard:service', args=[user_id])
                return redirect(f'{url}?year={year}&month={month}')
        except Exception:
            logger.exception(
                "サービス提供表の計画作成に失敗しました (user_id=%s, %s年%s月)",
                user_id,
                year,
                month,
            )
            messages.error(request, "計画を作成できませんでした。入力内容を確認してください。")
            return redirect("dashboard:user_list")
    #GETリクエスト
    messages.success(request, f'{year}年 {month}月分の適用曜日と時間を登録してください')
    prev:ServicePlan|None = _previous_record(user, year, month)
    initial = {
        'year':year,
        'month':month,
        'start_time':prev.start_time if prev else '09:00',
        'end_time':prev.end_time if prev else '17:00',
        'weekdays':prev.weekday_pattern if prev else [],
        'from_list':from_list
    }
    form = PlanForm(initial=initial,user_id=user_id)
    plans = ServicePlan.objects.filter(user = user,year = year,month = month,)
    user_code = plans.values_list("service_code",flat=True) #userチェック済みのサービスコード
    all_plans = list(ServiceMaster.objects #todo モデルに問い合わせるReact化
                     .exclude(service_code__in = user_code)
                     .filter(care_level = user.care_level)
                     .values()
                     )
    logger.info(f'{year}-{month}を作成する為のフォームを表示')

    context={'year':year,'month':month,'user':user,'form': form,'all_plans':all_plans, 'breadcrumbs': BreadcrumbUtil.create(crumbs)}
    return render(request,'dashboard/create_plan.html', context )

def _previous_record(user, year, month) -> ServiceMonthlyRecord | None:
    target_date = date(year, month, 1)
    return (
        user.monthly_records.filter(date__lt=target_date)
        .order_by("-date")
        .first()
    )