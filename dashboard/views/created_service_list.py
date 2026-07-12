from django.shortcuts import render
from dashboard.models import ServiceRecord

#利用者一覧
def created_service_list(request):
    records = ServiceRecord.objects.all().filter(confirmed=True).order_by('-date')
    return render(request, 'dashboard/created_service_list.html', {'records': records})