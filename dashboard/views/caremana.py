
from dashboard.models import CareManager, User
from dashboard.forms import CareManagerForm
from django.shortcuts import render,redirect,get_object_or_404
from employees.permissions import delete_permission_required

from django.contrib import messages
#ケアマネジャー一覧
def caremana_list(request):
    caremanagers = CareManager.objects.all()
    # caremanagers.users = [User.objects.filter(care_manager=caremanager) for caremanager in caremanagers]
    return render(request, 'dashboard/caremanager_list.html', {'caremanagers': caremanagers})

# @login_required
def caremana_update(request, caremanager_id):
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
    return render(request, 'dashboard/caremanager_update.html', {'form': form})

# @login_required
@delete_permission_required
def caremana_delete(request, caremanager_id):
    target = get_object_or_404(CareManager, id=caremanager_id)
    if request.method == 'POST':
        target.delete()
        return redirect('dashboard:caremana_list')
    return render(request,'dashboard/user_delete.html',{'user':target})


# ケアマネジャー情報1
def caremana_create(request):
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
    })

# # @login_required
# @require_POST
# def caremana_bulk_delete(request):
#     try:
#         # JSONデータをパース
#         data = json.loads(request.body)
#         ids = data.get('ids', [])
        
#         if ids:
#             # 指定されたIDのケアマネジャーを一括削除
#             deleted_count, _ = CareManager.objects.filter(id__in=ids).delete()
#             return JsonResponse({'status': 'ok', 'deleted_count': deleted_count})
        
#         return JsonResponse({'status': 'error', 'message': '削除対象が選択されていません'}, status=400)
    
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)