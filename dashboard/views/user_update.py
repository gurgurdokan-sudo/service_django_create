from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from dashboard.models import User
from dashboard.forms import UserForm

#更新
def user_update(request, user_id):
    user = get_object_or_404(User,id=user_id)
    title ='error' #titleの初期値を設定
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request,f'{user.name}さんを更新されました')
            return redirect('dashboard:user_list')
    else:
        form = UserForm(instance=user)
        title = f'{user.name} 基本情報 更新'
    return render(request, 'dashboard/user_form.html', {'form': form, 'title':title})