from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from dashboard.forms import UserForm, CertificateForm

#新規作成
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard:certificate_createt',user_id=user.id) # 認定情報作成画面へ遷移
    else:
        form = UserForm()
    return render(request,'dashboard/user_form.html', {'form': form})

def certificate_create(request,user_id):
    user = get_object_or_404(User,id = user_id)
    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = user
            cert.seav()
            messages.success(request,'新規登録完了しました')
            return redirect('dashboard:user_list')
    else: form = CertificateForm()
    return render(request, 'dashboard/user_form.html',{'form': form,'user': user})