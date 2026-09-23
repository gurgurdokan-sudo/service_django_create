from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages

from dashboard.models import CareManager
from dashboard.forms import CareManagerForm
from dashboard.utils import BreadcrumbUtil

from employees.permissions import delete_permission_required, has_delete_permission
#ケアマネジャー一覧
@login_required
def care_mana_list(request):
    crumbs = [("ケアマネジャー一覧", None)]
    can_delete = has_delete_permission(request.user)
    caremanagers = CareManager.objects.all()
    # caremanagers.users = [User.objects.filter(care_manager=caremanager) for caremanager in caremanagers]
    return render(request, 'dashboard/care_manager_list.html', {
        'caremanagers': caremanagers,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        'can_delete':can_delete,
    })

def care_mana_update(request, caremanager_id):
    caremanager = get_object_or_404(CareManager, id=caremanager_id)
    crumbs = [
        ("ケアマネジャー一覧", "dashboard:care_mana_list"),
        (f"{caremanager.name} 様 更新", None)
    ]
    if request.method == 'POST':
        form = CareManagerForm(request.POST, instance=caremanager)
        if form.is_valid():
            caremana = form.save(commit=False)
            caremana.name = caremana.name.replace('　',' ')
            caremana.save()
            return redirect('dashboard:care_mana_list')
    else:
        form = CareManagerForm(instance=caremanager)
    return render(request, 'dashboard/care_manager_update.html', {
        'form': form,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })

@delete_permission_required
def care_mana_delete(request, caremanager_id):
    target = get_object_or_404(CareManager, id=caremanager_id)
    crumbs = [
        ("ケアマネジャー一覧", "dashboard:care_mana_list"),
        (f"{target.name} 様 削除確認", None)
    ]
    if request.method == 'POST':
        target.delete()
        return redirect('dashboard:care_mana_list')
    return render(request,'dashboard/user_delete.html',{
        'user':target,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        })


# ケアマネジャー情報1 (利用者登録フローの途中)
@login_required
def care_mana_create(request):
    crumbs = [
        ("ケアマネジャー一覧", "dashboard:care_mana_list"),
        ("ケアマネジャー登録", None)
    ]
    care_managers = CareManager.objects.all()
    for cm in care_managers:
        if len(cm.office_name) >= 8:
            select_office_name = f'{cm.office_name[:5]}...'
        else:
            select_office_name = cm.office_name
        cm.select = f'{cm.name}({select_office_name})'

    if request.method == 'POST':
        if 'skip' in request.POST:
            selected_id = request.POST.get('existing_manager')
            if selected_id:
                return redirect('dashboard:create',cm_id= selected_id)
            else:
                messages.error(request, '既存マネジャーを選択してください')
        form = CareManagerForm(request.POST)
        if form.is_valid():
            care_mana = form.save(commit=False)
            care_mana.name = care_mana.name.replace('　', ' ')
            care_mana.save()
            return redirect('dashboard:create',cm_id=care_mana.id)  # user作成画面へ遷移

    else:
        form = CareManagerForm()
    return render(request, 'dashboard/care_manager_form.html', {
        'form': form,
        'title': 'ケアマネジャー登録',
        'caremanagers': care_managers,
        'breadcrumbs': BreadcrumbUtil.create(crumbs)
    })
