from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from .models import User

#利用者一覧
def user_list(request):
    users = User.objects.all()
    for user in users:
        user.has_plan = ServicePlan.objects.filter(user=user).first() is not None
    return render(request, 'dashboard/user_list.html', {'users': users})