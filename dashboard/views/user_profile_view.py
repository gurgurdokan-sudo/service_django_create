from datetime import date
from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404

from dashboard.forms import UserForm, PublicAssistanceForm
from dashboard.models import UseUser, CareManager, PublicAssistance
from dashboard.utils import BreadcrumbUtil

from employees.permissions import delete_permission_required

import logging
logger = logging.getLogger(__name__)

#利用者一覧
def user_list(request):
    users = UseUser.objects.all()
    return render(request, 'dashboard/user_list.html', {'users': users})

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
            user = form.save(commit=False)
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
    latest_pa = PublicAssistance.objects.filter(user= user,is_active = True).first()
    q_year = request.POST.get("year") or request.GET.get("year")
    q_month = request.POST.get("month") or request.GET.get("month")
    is_from_service = bool(q_year and q_month)

    crumbs =[
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様", "dashboard:detail", [user_id]), #詳細へ
        ("生活保護情報の登録", None)
    ]

    if request.method == 'POST':
        action = request.POST.get('action')
        logger.info(f'{action} ==========================================')
        try:
            y = int(q_year) if q_year else date.today().year
            m = int(q_month) if q_month else date.today().month
        except ValueError:
            y, m = date.today().year, date.today().month
        if action == 'release':
            # 「解除」リクエストの処理
            user.public_assistance.filter(is_active=True).update(is_active=False)
            url = reverse('dashboard:service', args=[user_id])
            return redirect(f'{url}?year={y}&month={m}')
        else:
            form = PublicAssistanceForm(request.POST)
            if form.is_valid():
                form.save(user=user,commit=False)
                messages.success(request, f"{user.name}様 の生活保護登録")
                if is_from_service:
                    url = reverse('dashboard:service', args=[user_id])
                    return redirect(f'{url}?year={y}&month={m}')
                else:
                    return redirect('dashboard:user_list')
    else: # GETリクエスト
        initial_data = {
            'start_year': latest_pa.start_date.year if latest_pa else None,
            'start_month': latest_pa.start_date.month if latest_pa else None,
            'hogo_number': latest_pa.hogo_number if latest_pa else '',
            'recipient_number': latest_pa.recipient_number if latest_pa else '',
        }
        form = PublicAssistanceForm(initial = initial_data)
    return render(request, 'dashboard/public_assistance_form.html',{
        'form': form,
        'user': user,
        'title': f'{user.name}様 生活保護登録',
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        'is_from_service' : is_from_service,
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
    user = get_object_or_404(
            UseUser.objects.prefetch_related('certificates', 'public_assistance'),
        id=user_id
    )
    certificates = user.certificates.order_by("-is_active","-limit_start")[:5]
    public_assistance = user.public_assistance.order_by("-is_active","-end_date")

    logger.info(f'{certificates}\n{public_assistance}')
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


