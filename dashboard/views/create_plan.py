from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from dashboard.models import User, ServicePlan, ServiceMaster
from dashboard.forms import PlanForm
from dashboard.calendar_table import get_month_days

def create_plan(request,user_id):
    if request.method == 'POST':
        form = PlanForm(request.POST,user_id=user_id)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user_id = user_id
            plan.build_schedule(form.cleaned_data['weekdays'])
            plan.apply_service_master() #コピー項目
            form.save()
            messages.success(request,'プランを作成しました')
            return redirect('dashboard:service',user_id=user_id)
    else:
        user = get_object_or_404(User, id= user_id)
        form = PlanForm(user_id=user_id)
    return render(request,'dashboard/create_plan.html', {
        'form': form,
        'user':user
        })
