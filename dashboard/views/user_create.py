from django.shortcuts import render,redirect
from django.contrib import messages
from dashboard.forms import UserForm

#新規作成
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'新規登録完了しました')
            return redirect('dashboard:user_list')
    else:
        form = UserForm()
    return render(request,'dashboard/user_form.html', {'form': form})