from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from dashboard.forms import UserForm, CertificateForm, CareManagerForm
from dashboard.models import User, CareManager
#ケアマネジャー情報
def caremana_create(request):
    caremanagers = CareManager.objects.all()
    for cm in caremanagers:
        if len(cm.office_name) >5: 
            select_name = f'{cm.office_name[:8]}...'
        else: select_name = cm.office_name
        cm.select = f'{cm.name}({select_name})'
        
    if request.method == 'POST':
        if 'skip' in request.POST:
            selected = request.POST.get('existing_manager')
            if selected:
                request.session['select_manager'] = selected
                return redirect('dashboard:create')
            else: messages.error(request,'既存マネジャーを選択してください')
        form = CareManagerForm(request.POST)
        if form.is_valid():
            caremana = form.save()
            request.session['select_manager'] = caremana.id
            return redirect('dashboard:create') # user作成画面へ遷移
    
    else: form = CareManagerForm()
    return render(request, 'dashboard/user_form.html',{
        'form': form, 
        'title':'ケアマネジャー登録',
        'caremanagers': caremanagers, 
        })

#新規作成
def user_create(request):
    cm_id = request.session.get('select_manager')
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.care_manager_id = cm_id
            user.save()
            return redirect('dashboard:certificate_create',user_id=user.id) # 認定情報作成画面へ遷移
    else: form = UserForm()
    return render(request,'dashboard/user_form.html', {
        'form': form,
        'title': '利用者の登録'
        })

#認定情報
def certificate_create(request,user_id):
    user = get_object_or_404(User,id = user_id)
    if request.method == 'POST':
        form = CertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = user
            cert.benefit_rate = user.benefit_rate
            cert.insured_number =user.insured_number
            cert.save()
            messages.success(request,'新規登録完了しました')
            return redirect('dashboard:user_list')
    else: form = CertificateForm()
    return render(request, 'dashboard/user_form.html',{
        'form': form,
        'user': user,
        'title': '利用者の介護保険被保険者証',
        'cetrificate': '1'
        })
