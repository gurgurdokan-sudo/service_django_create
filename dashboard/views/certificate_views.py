from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages

from dashboard.utils import BreadcrumbUtil
from dashboard.forms import CertificateForm
from dashboard.models import UseUser

import logging
logger = logging.getLogger(__name__)

def certificate_update(request, user_id):
    user = get_object_or_404(UseUser, id=user_id)
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様 詳細", "dashboard:detail", [user.id]),
        (f"認定情報更新", None),
    ]
    if request.method == 'POST':
        print("====================",flush=True)
        form = CertificateForm(request.POST)
        if form.is_valid():
             cert = form.save(commit=False)
             cert.pk = None
             cert.user = user
             cert_origin = user.certificates.filter(is_active=True).first()
             limit_strat = cert_origin.limit_start if cert_origin else None
             limit_end = cert_origin.limit_end if cert_origin else None
             if (limit_strat >= cert.limit_strat >= limit_end and
                     cert_origin.care_level == cert.care_level):
                    messages.error(request,'更新日が範囲外です')
                    return redirect('dashboard:detail', user_id=user.id)
             # 前回の認定情報を無効化
             cert_origin.update(is_active=False)
            
             cert.care_level_changed_at = form.cleaned_data['limit_start']
             cert.is_active = True
            
             cert.save()
        messages.success(request, '認定情報を更新しました。')
        return redirect('dashboard:detail', user_id=user.id)
    else:
        instance = user.certificates.filter(is_active=True).first()
        form = CertificateForm(instance=instance)  # 初期値として最初の認定情報を使用
        context = {
            'user': user,
            'form': form,
            'breadcrumbs': BreadcrumbUtil.create(crumbs),
            'update': True,
            'title': '認定情報更新',
        }
        return render(request, 'dashboard/certificate_form.html', context)

#認定情報3
def certificate_create(request,user_id):
    user = get_object_or_404(UseUser,id = user_id)

    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様", None),
        ("被保険者証情報の登録", None)
    ]

    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = user
            # cert.benefit_rate = user.benefit_rate #負担割合をコピーする
            cert.insured_number =user.insured_number
            cert.save()
            messages.success(request,f'{user.name}様 新規登録完了しました')
            flag =form.cleaned_data.get('public_assistance_flag')
            if flag:
                logger.info(f'生活保護 : {flag}')
                return redirect('dashboard:public_assistance_create',user_id=user.id)
            return redirect('dashboard:user_list')
    else: form = CertificateForm()
    return render(request, 'dashboard/certificate_form.html',{
        'form': form,
        'user': user,
        'title': '利用者の介護保険被保険者証登録',
        'cetrificate': '1',
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })