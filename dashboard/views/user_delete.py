from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from dashboard.models import User

from employees.permissions import delete_permission_required

@delete_permission_required
def user_delete(request,user_id):
    target = get_object_or_404(User,id=user_id)
    if request.method=='POST':
        messages.error(request,f'{target.name}さんを消去しました')
        target.delete()
        return redirect('dashboard:user_list')
    return render(request,'dashboard/user_delete.html',{'user':target})
