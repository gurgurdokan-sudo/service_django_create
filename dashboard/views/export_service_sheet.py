import os
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404,render, redirect
from dashboard.models import User, ServicePlan, ServiceMaster
from dashboard.calendar_table import get_month_days
from dashboard.excel.service_sheet import get_service_sheet_path
# Excel ダウンロード（既に作成済みのファイルを返す）
def download_service_sheet(request, user_id):
    user = get_object_or_404(User, id=user_id)
    year = int(request.GET.get('year'))
    month = int(request.GET.get('month'))
    file_path, filename = get_service_sheet_path(user, year, month)

    if not file_path or not os.path.exists(file_path):
        messages.error(request, 'ファイルが作成されていません')
        return redirect('dashboard:service', user_id=user_id)

    with open(file_path, 'rb') as f:
        response = HttpResponse(
            f.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
