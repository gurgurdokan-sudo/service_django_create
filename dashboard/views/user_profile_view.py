import calendar
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.db.models import QuerySet, Prefetch
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from dashboard.forms import UserForm, PublicAssistanceForm
from dashboard.models import(
                                UseUser,
                                CareManager,
                                PublicAssistance,
                                Certificate,
                                ServiceMonthlyRecord
                            )
from dashboard.utils import BreadcrumbUtil
from employees.permissions import delete_permission_required
import logging
logger = logging.getLogger(__name__)

#利用者一覧
def user_list(request):
    today = timezone.localdate()
    current_month_start = today.replace(day=1)
    next_month_start = current_month_start + relativedelta(months=1)
    current_month = (today.year, today.month)
    next_month = (next_month_start.year, next_month_start.month)

    last_day = calendar.monthrange(today.year, today.month)[1]
    month_end = today.replace(day=last_day)
    is_within_ten_days_of_month_end = today >= month_end - timedelta(days=10)

    # 月末が近いときだけ、当月の未確定記録を取得
    unconfirmed_user_ids = set()
    if is_within_ten_days_of_month_end:
        unconfirmed_user_ids = set(
            ServiceMonthlyRecord.objects
            .filter(date=current_month_start, confirmed=False)
            .values_list("user_id", flat=True)
        )
    # 毎回DBを引かないよう、有効な認定を事前取得
    valid_certificates = (
        Certificate.objects
        .filter(limit_start__lte=today, limit_end__gte=today)
        .order_by("-limit_start")
    )
    users: QuerySet[UseUser] = (
        UseUser.objects
        .select_related("care_manager")
        .prefetch_related(
            Prefetch("certificates",queryset=valid_certificates,to_attr="valid_certificates")
        )
    )
    alerts = []
    for user in users:
        if user.care_manager_id is None:
            alerts.append(
                f"{user.name} 様のケアマネジャーが紐づいていません。"
                "詳細画面で設定してください"
            )

        certificate = (
            user.valid_certificates[0]
            if user.valid_certificates
            else None
        )

        if certificate is None:
            alerts.append(
                f"{user.name} 様の有効な介護認定がありません。"
                "詳細画面で介護認定を設定してください"
            )
        else:
            changed_at = certificate.care_level_changed_at
            if changed_at is not None:
                changed_month = (changed_at.year, changed_at.month)

                if changed_month == current_month:
                    alerts.append(
                        f"{user.name} 様の介護認定が今月で切り替わります"
                    )
                elif changed_month == next_month:
                    alerts.append(
                        f"{user.name} 様の介護認定が来月で切り替わります"
                    )

        # 認定情報の有無にかかわらず、月末通知を判定する
        if (
                is_within_ten_days_of_month_end
                and user.pk in unconfirmed_user_ids
        ):
            alerts.append(
                f"{user.name} 様のサービス提供表を確定させてください"
            )

    return render(request, 'dashboard/user_list.html', {
        'users': users,
        'alerts': alerts,
    })
#新規作成2
def user_create(request, cm_id):
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        ("利用者新規登録", None)
    ]
    care_maneger = get_object_or_404(CareManager, id= cm_id)
    cm_name = f'{care_maneger.name} ({care_maneger.office_name})'
    if request.method == 'POST':
        logger.info('新規作成post')
        form = UserForm(request.POST)
        if form.is_valid():
            user:UseUser = form.save(commit=False)
            user.care_manager_id = cm_id
            user.save()
            return redirect('dashboard:certificate_create',user_id=user.id) # 認定情報作成画面へ遷移
    else: form = UserForm(initial={'benefit_rate':0.9})
    return render(request,'dashboard/new_user_form.html', {
        'cm_name' :cm_name,
        'form': form,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })


#生活保護情報4
def public_assistance_create(request,user_id):
    user = get_object_or_404(UseUser,id = user_id)
    latest_pa:PublicAssistance = PublicAssistance.objects.filter(user= user,is_active = True).first()
    q_year = request.POST.get("year") or request.GET.get("year")
    q_month = request.POST.get("month") or request.GET.get("month")
    from_list = request.GET.get("from_list") or 0
    is_from_service = bool(q_year and q_month)
    linking = request.POST.get("linking") or request.GET.get("linking") # 詳細から遷移flag
    crumbs =[
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様", "dashboard:detail", [user_id]), #詳細へ
        ("生活保護情報の登録", None)
    ]
    try:
        y = int(q_year) if q_year else date.today().year
        m = int(q_month) if q_month else date.today().month
    except ValueError:
        y, m = date.today().year, date.today().month
    initial_data = {
        'start_year': y,
        'start_month': m,
        'hogo_number': latest_pa.hogo_number if latest_pa else '',
        'recipient_number': latest_pa.recipient_number if latest_pa else '',
        'linking': linking,
    }
    form = PublicAssistanceForm(request.POST or None,initial=initial_data)

    if request.method == 'POST':
        action = request.POST.get('action')
        logger.info('生活保護_create POST start ,action=%s ,user_name=%s',action, user.name)
        # form.instance.user = user
        if action == 'release':
            # 「解除」リクエストの処理
            user.public_assistance.filter(is_active=True).update(is_active=False)
            url = reverse('dashboard:service', args=[user_id])
            return redirect(f'生活保護を解除 redirect {url}?year={y}&month={m}')

        elif form.is_valid():
            form.save(user=user)
            messages.success(request, f"{user.name}様 の生活保護登録")
            if is_from_service:
                url = reverse('dashboard:service', args=[user_id])
                logger.info(f'新規 生活保護を登録 redirect {url}?year={y}&month={m}')
                return redirect(f'{url}?year={y}&month={m}&from_list={from_list}')
            elif linking:
                logger.info('詳細から 生活保護を登録 or 追加, user_name=%s, year=%d, month=%d',
                            user.name, y, m)
                return redirect('dashboard:detail', user_id)
            else:
                return redirect('dashboard:user_list')

    return render(request, 'dashboard/public_assistance_form.html',{
        'form': form,
        'user': user,
        'title': f'{user.name}様 生活保護登録',
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        'is_from_service' : is_from_service,
        'linking': linking,
    })

def public_assistance_edit(request, user_id, public_assistance_id):
    user = get_object_or_404(UseUser,id = user_id)
    public_assistance = get_object_or_404(PublicAssistance,id = public_assistance_id)
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様", "dashboard:detail", [user_id]),  # 詳細へ
        ("生活保護情報の登録", None)
    ]
    form = PublicAssistanceForm(request.POST or None,instance=public_assistance)
    if request.method == 'POST' :
        action = request.POST.get('action')
        if action == 'release':
            # 「解除」リクエストの処理
            public_assistance.delete()
            messages.success(request, f"{user.name}様 の生活保護情報を消去しました")
            return redirect('dashboard:detail', user_id )
        if form.is_valid():
            form.save(user=user)
            messages.success(request, f"{user.name}様 の生活保護情報を更新しました")
            return redirect('dashboard:detail', user_id )
    return render(request, 'dashboard/public_assistance_form.html', {
        'user': user,
        'form': form,
        'title': f'{user.name}様 生活保護',
        'edit': True,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })

#消去
@delete_permission_required
def user_delete(request, user_id):
    target = get_object_or_404(UseUser, id=user_id)
    
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        (f"{target.name} 様 詳細", "dashboard:detail", [target.id]),
        ("削除の確認", None)
    ]

    if request.method == 'POST':
        messages.error(request, f'{target.name} 様のデータを削除しました。') 
        target.delete()
        return redirect('dashboard:user_list')
        
    # GET
    return render(request, 'dashboard/user_delete.html', {
        'user': target,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })

# 更新
def user_update(request, user_id):
    user = get_object_or_404(UseUser, id=user_id)
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様 詳細", "dashboard:detail", [user.id]),
        ("基本情報更新", None),
    ]
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'{user.name} さんの情報を更新しました')
            return redirect('dashboard:detail', user_id=user.id)
    else:
        form = UserForm(instance=user)

    # ケアマネが紐付いていれば名前を取得、いなければ None
    cm_name = user.care_manager.name if user.care_manager else None
    return render(request, 'dashboard/new_user_form.html', {
        'title': f'{user.name} 基本情報 更新',
        'form': form,
        'cm_name': cm_name,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })


#詳細（JSのbutton遷移で消去
def user_detail(request, user_id):
    # 履歴もまとめて取得
    user:UseUser = get_object_or_404(
        UseUser.objects.prefetch_related('certificates', 'public_assistance'),
        id=user_id
    )
    certificates:QuerySet[Certificate] = user.certificates.order_by("-is_active","-limit_start")[:5]
    public_assistance:QuerySet[PublicAssistance] = user.public_assistance.order_by("-is_active","-end_date")[:5]

    logger.info(f'\n介護認定={certificates}\n生活保護={public_assistance}')
    labels = {f.name: f.verbose_name for f in user._meta.fields}
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様 詳細", None)
    ]

    context = {
        'user': user,
        'certificates': certificates,
        'public_assistance': public_assistance,
        'labels': labels,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    }

    return render(request, 'dashboard/user_detail.html', context)


