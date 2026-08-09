from django.shortcuts import render
from dashboard.models import ServiceMonthlyRecord

#利用者一覧
def created_service_list(request):
    records = ServiceMonthlyRecord.objects.all().filter(confirmed=True).order_by('-date')
    return render(request, 'dashboard/created_service_list.html', {'records': records})

from django.http import JsonResponse

def created_service_list_api(request):
    year = request.GET.get('year')
    month = request.GET.get('month')

    records = ServiceMonthlyRecord.objects.filter(
        confirmed=True,
        date__year=year,
        date__month=month
    ).order_by('-date')
    data = [
        {
            "user": record.user.name,
            "date": record.date.strftime("%Y-%m"),
            "confirmed": record.confirmed,
            "download_url": f"/dashboard/download_service_sheet/{record.user.id}?dis_year={record.date.year}&dis_month={record.date.month}"
        }
        for record in records
    ]
    return JsonResponse({"records": data})
