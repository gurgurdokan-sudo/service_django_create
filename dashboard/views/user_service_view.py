from datetime import date
from django.shortcuts import render,redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse

from dashboard.utils import BreadcrumbUtil
from dashboard.models import(
    UseUser,
    ServicePlan, 
    ServiceMaster,
    AddOnService,
    Office,
    ServiceMonthlyRecord,
)
from dashboard.calendar_table import get_month_days
now = timezone.now()

import logging
logger = logging.getLogger(__name__)

def build_user_service_context(user_id, year, month):
    """画面やExcelに渡すcontextを組み立てる"""
    office = Office.objects.filter(id=1).first() #todoログインユーザー事務所
    default = AddOnService.objects.get(pk=office.default_service.pk)

    target = (UseUser.objects.select_related('care_manager').get(id=user_id))
    monthly_record = target.get_monthly_record(year, month)
    plans = ServicePlan.objects.filter(user = target,year = year,month = month,)
    addons = []
    for p in plans:
        summary = p.get_addon_summary
        for key, item in summary.items():
            addon = item.get("addon")
            days = item.get("days", [])
            if not addon:
                continue
            addons.append({
                "p_id": p.id,
                "id": addon.id,
                "name": addon.service_name,
                "days": days,
                "total": len(days),
            })
    print(addons)
    logger.info(f'{year}-{month}のサービス提供票のplansを取得')

    user_codes = plans.values_list("service_code",flat=True) #userチェック済みのサービスコード
    all_plans = (
        ServiceMaster.objects
        .filter(care_level=target.get_certificate(year, month))
        .exclude(service_code__in = user_codes)
        )
    logger.info(f'{user_codes}以外のplansを取得')

    addon_service = AddOnService.objects.all()
    logger.info(f'{year}-{month}のサービス提供票の確認状態を取得')
    record = ServiceMonthlyRecord.objects.filter(user=target, date=date(year, month, 1)).first()

    return {
        'office': office,
        'default': default,
        'user': target,
        'plans': plans,
        'addons':addons,
        'calendar': get_month_days(year, month),
        'dis_year': year,
        'dis_month': month,
        'current_year': now.year, #Excel出力の表示用
        'current_month': now.month,

        # 画面用　batchアラート
        'monthly_record': monthly_record, # サービス提供票の確定状態
        'public_assistance':target.get_public_assistance(year,month),
        # 画面用　Flag
        'confirmed': record.confirmed if record else False,
        # 画面用　select移動範囲
        'year_range': range(now.year - 1, now.year + 1),
        'month_range': range(1, 13),
        # 画面用　モーダルに出すPlan/Addon
        'addon_service': addon_service,
        'service': all_plans,  # userの対象全プラン
    }

def _is_future_month_not_plan(user, year, month, prev=False):
    """指定された年月が未来で、かつその月のプランが存在しない場合にTrueを返す"""
    if prev:
        return not ServicePlan.objects.filter(user=user, year=year, month=month).exists()
    if (year > now.year) or (year == now.year and month >= now.month):
        return not ServicePlan.objects.filter(user=user, year=year, month=month).exists()
    return False


def _is_future_month_not_pa(user, year, month, prev=False):
    """指定された年月が「今月以降」で、生保利用者データがない場合にTrue"""
    if not user.is_public_assistance_for_month: return False
    target_date = date(year, month, 1)
    if ServiceMonthlyRecord.objects.filter(user=user,date=target_date).first():
        return False
        
    if user.get_public_assistance(year, month): return False

    if prev: return True

    today = date.today()
    this_month_first = date(today.year, today.month, 1)
    target_month_first = date(int(year), int(month), 1)    
    return target_month_first >= this_month_first

#main
def user_service(request,user_id):
    dis_year = int(request.GET.get('year', now.year))
    dis_month = int(request.GET.get('month', now.month))
    user = UseUser.objects.get(id=user_id)

# ケアマネジャーor認定情報更新が必要 利用者一覧画面にリダイレクトする
    if not user.care_manager or user.care_level == '認定情報更新が必要':
        logger.error(f'{user.name} で、認定情報orケアマネジャーが紐づけられてません')
        messages.error(request,'認定情報またはケアマネジャーが設定されてません')
        return redirect('dashboard:user_list')

#「今月の生保データ」が未登録なのに、「前月は生保だった」場合、先に生保登録へ誘導
    if _is_future_month_not_pa(user, dis_year, dis_month):
        messages.error(request, f'前月が生活保護受給のため、{dis_month}月分の情報を先に登録してください')
        url = reverse('dashboard:public_assistance_create', args=[user.id] )
        return redirect(f'{url}?year={dis_year}&month={dis_month}')

# 過去月のプラン作成 ではなく、プラン未作成なら作成画面にリダイレクトする
    if _is_future_month_not_plan(user_id,dis_year, dis_month):
        request.check_flag = True
        url = reverse('dashboard:createPlan', args=[user_id] )
        return redirect(f'{url}?year={dis_year}&month={dis_month}')

    logger.info(f'{dis_year}-{dis_month}のサービス提供票に遷移')
    context = build_user_service_context(user_id=user_id,year=dis_year,month=dis_month)
    crumbs = [
        (f"{user.name}様 サービス提供表作成", None)
    ]
    context['breadcrumbs'] = BreadcrumbUtil.create(crumbs)
    logger.info(f'======{user.name} 様 提供表確定 {context["confirmed"]}======')
    print(context,flush=True)
    return render(request,'dashboard/user_service.html',context)

#一括前月モード
def prev_month_plan(request, user_id):
    prev_month = now.month - 1 if now.month > 1 else 12
    year = now.year if prev_month != 12 else now.year - 1
    if _is_future_month_not_plan(user_id,year,prev_month,prev=True):
        url = reverse('dashboard:createPlan', args=[user_id] )
        return redirect(
            f'{url}?year={year}&month={prev_month}'
            )
    if _is_future_month_not_pa(UseUser.objects.get(id=user_id),year,prev_month,prev=True):
        url = reverse('dashboard:public_assistance_create', args=[user_id] )
        return redirect(
            f'{url}?year={year}&month={prev_month}'
            )
    logger.info(f'prev{year}-{prev_month}のサービス提供票に遷移')
    context = build_user_service_context(user_id=user_id,year=year,month=prev_month)
    return render(request,'dashboard/user_service.html',context)

#予定通り
def service_act(request, user_id):
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))

    col = get_month_days(year=year, month=month)
    user = get_object_or_404(UseUser, id=user_id)

    query_plans = ServicePlan.objects.filter(
        user=user,
        year=year,
        month=month
    )

    for plan in query_plans:
        schedule = plan.schedule_dict      # {"1": "1", "5": "1", ...}
        actual = plan.actual_dict          # {"1": {"main": "", "addon": []}, ...}

        for day in col:
            day_str = str(day['day'])
            if schedule.get(day_str) == '1':
                actual[day_str]['main'] = '1'
            else:
                actual[day_str]['main'] = ''

        plan.actual_json = actual
        plan.save()

    messages.success(request, '予定で実績を作成しました')
    return redirect(f"{reverse('dashboard:service', args=[user_id])}?year={year}&month={month}")
