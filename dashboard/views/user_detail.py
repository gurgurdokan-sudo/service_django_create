from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from dashboard.forms import CertificateUpdateForm
from dashboard.models import User, Certificate

#詳細（JSのboutton遷移で消去
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
#介護認定変更 is_superuserのときのみ表示など考えてる
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
        'labels':labels
    })