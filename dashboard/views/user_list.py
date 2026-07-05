from django.shortcuts import render
from dashboard.models import User, ServicePlan

#利用者一覧
def user_list(request):
    users = User.objects.all()
    for user in users:
        user.has_plan = ServicePlan.objects.filter(user=user).first() is not None
    return render(request, 'dashboard/user_list.html', {'users': users})