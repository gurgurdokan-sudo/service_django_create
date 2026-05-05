from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import User

#詳細
def user_detail(request,user_id):
    target = get_object_or_404(User,id=user_id)
    labels = {f.name: f.verbose_name for f in target._meta.fields}
    return render(request,'dashboard/user_detail.html',{'user': target,'labels': labels,})