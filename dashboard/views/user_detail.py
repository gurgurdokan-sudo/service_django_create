from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from dashboard.forms import CertificateUpdateForm
from dashboard.models import User, Certificate

#詳細
def user_detail(request,user_id):
    user = get_object_or_404(User,id=user_id)
    if request.method =='POST':
        form = CertificateUpdateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = user
            # User から変わらない情報
            cert.benefit_rate = user.benefit_rate
            cert.insured_number = user.insured_number
            # 変更日は開始日と同じ
            cert.care_level_changed_at = cert.limit_start
            cert.save()
            messages.success(request,'介護認定の登録が完了しました')
            return redirect('dashboard:user_list')
    else: form = CertificateUpdateForm()
    labels = {f.name: f.verbose_name for f in user._meta.fields}
    return render(request,'dashboard/user_detail.html',{
        'user': user,
        'labels': labels,
        'form':form
        })