from django.shortcuts import render,redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse

from dashboard.utils import BreadcrumbUtil
from dashboard.forms import CertificateForm
from dashboard.models import(
    User,
    Certificate,
)
from dashboard.calendar_table import get_month_days

import logging
logger = logging.getLogger(__name__)

def certificate_update(request, user_id):
    user = get_object_or_404(User, id=user_id)
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        (f"{user.name} 様 詳細", "dashboard:detail", [user.id]),
        (f"認定情報更新", None),
    ]
    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = user
            # 前回の認定情報を無効化&変更日を設定
            if Certificate.objects.filter(user=user).first():
                user.certificate.update(is_active=False, change_date=form.cleaned_data['start_date'])
            cert.care_level_changed_at = form.cleaned_data['limit_start']
            cert.is_active = True
            
            cert.save()
        messages.success(request, '認定情報を更新しました。')
        return redirect('dashboard:detail', user_id=user.id)
    else:
        instance = user.certificate.first(is_active=True).first() if user.certificate.exists() else None
        form = CertificateForm(instance=instance)  # 初期値として最初の認定情報を使用
        context = {
            'user': user,
            'form': form,
            'breadcrumbs': BreadcrumbUtil.create(crumbs),
            'update': True,
            'title': '認定情報更新',
        }
        return render(request, 'dashboard/certificate_form.html', context)