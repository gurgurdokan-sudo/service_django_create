from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from dashboard.forms import UserForm, CertificateForm, CertificateUpdateForm, PublicAssistanceForm
from dashboard.models import User, CareManager
from dashboard.utils import BreadcrumbUtil

from employees.permissions import delete_permission_required

import logging
logger = logging.getLogger(__name__)

#利用者一覧
def user_list(request):
    users = User.objects.all()
    return render(request, 'dashboard/user_list.html', {'users': users})

#新規作成2
def user_create(request, cm_id):
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        ("利用者新規登録", None)
    ]
    caremaneger = get_object_or_404(CareManager, id= cm_id)
    cm_name = f'{caremaneger.name} ({caremaneger.office_name})'
    if request.method == 'POST':
        logger.info('新規作成post')
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.name = user.name.replace('　',' ')
            user.name_kana = user.name_kana.replace('　',' ')
            user.care_manager_id = cm_id
            user.save()
            return redirect('dashboard:certificate_create',user_id=user.id) # 認定情報作成画面へ遷移
    else: form = UserForm(initial={'benefit_rate':0.9})
    return render(request,'dashboard/new_user_form.html', {
        'cm_name' :cm_name,
        'form': form,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })

#認定情報3
def certificate_create(request,user_id):
    user = get_object_or_404(User,id = user_id)
    crumbs = [
        # ("利用者一覧", reverse("dashboard:user_list")),
        (f"{user.name} 様", None),
        ("被保険者証情報の登録", None)
    ]

    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = user
            cert.benefit_rate = user.benefit_rate
            cert.insured_number =user.insured_number
            cert.save()
            messages.success(request,f'{user.name}様 新規登録完了しました')
            if form.cleaned_data.get('public_assistance_flag'): redirect('dashboard:public_assistance_create',user_id=user.id)
            return redirect('dashboard:user_list')
    else: form = CertificateForm()
    return render(request, 'dashboard/user_form.html',{
        'form': form,
        'user': user,
        'title': '利用者の介護保険被保険者証登録',
        'cetrificate': '1',
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })
#生活保護情報4
def public_assistance_create(request,user_id):
    user = get_object_or_404(User,id = user_id)
    crumbs =[
        (f"{user.name} 様", "dashborad:delete"), #詳細へ
        ("生活保護情報の登録", None)
    ]
    if request.method == 'POST':
        form = PublicAssistanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, f"{user.name}様 の生活保護登録")
            return redirect('dashboard:user_list')
    else: form = PublicAssistanceForm()
    return render(request, 'dashboard/user_form.html',{
        'form': form,
        'user': user,
        'title': '利用者の生活保護登録',
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })
#消去
def user_delete(request,user_id):
    target = get_object_or_404(User,id=user_id)
    crumbs = [
        # ("利用者一覧", reverse("dashboard:user_list")),
        (f"{target.name} 様 詳細", reverse("dashboard:user_detail", args=[target.id])),
        ("削除確認", None)
    ]

    if request.method=='POST':
        messages.error(request,f'{target.name}さんを消去しました')
        target.delete()
        return redirect('dashboard:user_list')
    return render(request,'dashboard/user_delete.html',{
        'user':target,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })

#更新
def user_update(request, user_id):
    user = get_object_or_404(User,id=user_id)
    title ='error' #titleの初期値を設定
    crumbs = [
        (f"{user.name}様 更新画面",None),
    ]
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request,f'{user.name}さんを更新されました')
            return redirect('dashboard:user_list')
    else:
        form = UserForm(instance=user)
        title = f'{user.name} 基本情報 更新'
    return render(request, 'dashboard/user_form.html', {
        'title':title,
        'form': form,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })


#詳細（JSのbutton遷移で消去
@delete_permission_required
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    labels = {f.name: f.verbose_name for f in user._meta.fields}
    prev_cert = user.certificate.order_by('-limit_end').first() #現在適用中
    initial = {}
    if prev_cert:
        initial = {
            'care_level': prev_cert.care_level,
            'limit_amount_type': prev_cert.limit_amount_type,
            'limit_start': prev_cert.limit_start,
            'limit_end': prev_cert.limit_end,
        }
#介護認定変更 
    if request.method == 'POST':
        form = CertificateUpdateForm(request.POST)

        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = user
            cert.benefit_rate = user.benefit_rate
            cert.insured_number = user.insured_number
            if prev_cert: cert.care_level_changed_at = cert.limit_start
            cert.save()

            messages.success(request, '介護認定の更新が完了しました')
            return redirect('dashboard:user_list')
    else: form = CertificateUpdateForm(initial=initial)

    return render(request, 'dashboard/user_detail.html', {
        'user': user,
        'form': form,
        'labels':labels,
        # 'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })

