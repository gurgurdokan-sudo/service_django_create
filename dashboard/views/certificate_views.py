from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages

from dashboard.models import UseUser
from dashboard.utils import BreadcrumbUtil
from dashboard.forms import CertificateForm


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
        form = CertificateForm(request.POST)
        if form.is_valid():
             form.save(user=user)
             messages.success(request, '認定情報を更新しました。')
             return redirect('dashboard:detail', user_id=user.id)
        else:
            context = {
                'user': user,
                'form': form,
                'breadcrumbs': BreadcrumbUtil.create(crumbs),
                'update': True,
                'title': '認定情報更新',
            }
            return render(request, 'dashboard/certificate_form.html', context)
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
        (f"{user.name} 様", "dashboard:detail", [user.id]),
        ("被保険者証情報の登録", None)
    ]

    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            form.save(user=user)
            messages.success(request,f'{user.name}様 新規登録完了しました')

            flag =form.cleaned_data.get('public_assistance_flag')
            logger.info(f'生活保護 : {flag}')

            if flag:
                return redirect('dashboard:public_assistance_create',user_id=user.id)
            return redirect('dashboard:user_list')
    else: form = CertificateForm(initial={'insured_number': user.insured_number})
    return render(request, 'dashboard/certificate_form.html',{
        'form': form,
        'user': user,
        'title': '利用者の介護保険被保険者証登録',
        'cetrificate': '1',
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })