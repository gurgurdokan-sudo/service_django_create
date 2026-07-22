import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from dashboard.models import CareManager, User
from dashboard.forms import CareManagerForm
from django.shortcuts import render,redirect,get_object_or_404
from employees.permissions import delete_permission_required
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