from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages

from dashboard.models import CareManager, UseUser
from dashboard.forms import CareManagerForm
from dashboard.utils import BreadcrumbUtil

from employees.permissions import delete_permission_required, has_delete_permission
#ケアマネジャー一覧
@login_required
def care_mana_list(request):
    crumbs = [("ケアマネジャー一覧", None)]
    can_delete = has_delete_permission(request.user)
    care_managers = CareManager.objects.prefetch_related('useuser_set').order_by('name')
    return render(request, 'dashboard/care_manager_list.html', {
        'care_managers': care_managers,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
        'can_delete': can_delete,
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
        'caremanager': caremanager,
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
    user_id = request.POST.get('user_id') or request.GET.get('user_id')
    target_user = get_object_or_404(UseUser, id=user_id) if user_id else None

    if target_user:
        crumbs = [
            (f"{target_user.name} 様 詳細", "dashboard:detail", [target_user.id]),
            ("ケアマネジャー設定", None),
        ]
        title = f'{target_user.name} 様 ケアマネジャー設定'
    else:
        crumbs = [
            ("ケアマネジャー一覧", "dashboard:care_mana_list"),
            ("ケアマネジャー登録", None),
        ]
        title = 'ケアマネジャー登録'

    care_managers = CareManager.objects.all()
    for cm in care_managers:
        office = cm.office_name or ''
        short = f'{office[:5]}...' if len(office) >= 8 else office
        cm.select = f'{cm.name}({short})'

    form = CareManagerForm()
    if request.method == 'POST':
        if 'skip' in request.POST:
            # 既存のケアマネジャーを選んだ場合
            selected_id = request.POST.get('existing_manager')
            if not selected_id:
                messages.error(request, '既存マネジャーを選択してください')
            else:
                cm = get_object_or_404(CareManager, id=selected_id)
                if target_user:
                    target_user.care_manager = cm
                    target_user.save(update_fields=['care_manager'])
                    messages.success(request, f'{target_user.name} 様のケアマネジャーを {cm.name} に設定しました')
                    return redirect('dashboard:detail', user_id=target_user.id)
                return redirect('dashboard:create', cm_id=cm.id)
        else:
            # 新しいケアマネジャーを登録する場合
            form = CareManagerForm(request.POST)
            if form.is_valid():
                care_mana = form.save(commit=False)
                care_mana.name = care_mana.name.replace('　', ' ')
                care_mana.save()
                if target_user:
                    target_user.care_manager = care_mana
                    target_user.save(update_fields=['care_manager'])
                    messages.success(request, f'{target_user.name} 様のケアマネジャーを登録しました')
                    return redirect('dashboard:detail', user_id=target_user.id)
                return redirect('dashboard:create', cm_id=care_mana.id)  # 利用者作成画面へ

    return render(request, 'dashboard/care_manager_form.html', {
        'form': form,
        'title': title,
        'care_managers': care_managers,
        'target_user': target_user,
        'breadcrumbs': BreadcrumbUtil.create(crumbs),
    })