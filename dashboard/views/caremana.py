from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse

from dashboard.models import CareManager, User
from dashboard.forms import CareManagerForm
from dashboard.utils import BreadcrumbUtil

from employees.permissions import delete_permission_required
from django.contrib import messages
#ケアマネジャー一覧
@login_required
def caremana_list(request):
    crumbs = [("ケアマネジャー一覧", None)]
    caremanagers = CareManager.objects.all()
    # caremanagers.users = [User.objects.filter(care_manager=caremanager) for caremanager in caremanagers]
    return render(request, 'dashboard/caremanager_list.html', {
        'caremanagers': caremanagers,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })

def caremana_update(request, caremanager_id):
    crumbs = [
        ("ケアマネジャー一覧", reverse("dashboard:caremana_list")),
        (f"{caremanager.name} 様 更新", None)
    ]
    caremanager = get_object_or_404(CareManager, id=caremanager_id)
    if request.method == 'POST':
        form = CareManagerForm(request.POST, instance=caremanager)
        if form.is_valid():
            caremana = form.save(commit=False)
            caremana.name = caremana.name.replace('　',' ')
            caremana.save()
            return redirect('dashboard:caremana_list')
    else:
        form = CareManagerForm(instance=caremanager)
    return render(request, 'dashboard/caremanager_update.html', {
        'form': form,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })

@delete_permission_required
def caremana_delete(request, caremanager_id):
    crumbs = [
        ("ケアマネジャー一覧", reverse("dashboard:caremana_list")),
        (f"{target.name} 様 削除確認", None)
    ]
    target = get_object_or_404(CareManager, id=caremanager_id)
    if request.method == 'POST':
        target.delete()
        return redirect('dashboard:caremana_list')
    return render(request,'dashboard/user_delete.html',{
        'user':target,
        'breadcrumbs': BreadcrumbUtil.create(crumbs)
        })


# ケアマネジャー情報1 (利用者登録フローの途中)
@login_required
def caremana_create(request):
    crumbs = [
        ("利用者一覧", reverse("dashboard:user_list")),
        ("ケアマネジャー登録", None)
    ]
    caremanagers = CareManager.objects.all()
    for cm in caremanagers:
        if len(cm.office_name) > 5:
            select_name = f'{cm.office_name[:8]}...'
        else:
            select_name = cm.office_name
        cm.select = f'{cm.name}({select_name})'

    if request.method == 'POST':
        if 'skip' in request.POST:
            selected = request.POST.get('existing_manager')
            if selected:
                request.session['select_manager'] = selected
                return redirect('dashboard:create')
            else:
                messages.error(request, '既存マネジャーを選択してください')
        form = CareManagerForm(request.POST)
        if form.is_valid():
            caremana = form.save(commit=False)
            caremana.name = caremana.name.replace('　', ' ')
            caremana.save()
            request.session['select_manager'] = caremana.id
            return redirect('dashboard:create')  # user作成画面へ遷移

    else:
        form = CareManagerForm()
    return render(request, 'dashboard/user_form.html', {
        'form': form,
        'title': 'ケアマネジャー登録',
        'caremanagers': caremanagers,
        'breadcrumbs': BreadcrumbUtil.create(crumbs)
    })
