import os
import openpyxl
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from dashboard.models import UseUser
from dashboard.excel.excel_writer import get_service_sheet_path

def view_service_sheet(request, user_id):
    user = get_object_or_404(UseUser, id=user_id)
    year = int(request.GET.get('dis_year',2000))
    month = int(request.GET.get('dis_month',1))
    filepath, filename = get_service_sheet_path(user, year, month)

    if not filepath or not os.path.exists(filepath):
        messages.error(request, 'ファイルが作成されていません')
        return redirect('dashboard:service', user_id=user_id)

    wb = openpyxl.load_workbook(filepath)
    ws = wb.active

    table = []
    for row in ws.iter_rows(values_only=True):
        table.append(row)

    return render(request, "dashboard/view_sheet.html", {
        "user": user,
        "year": year,
        "month": month,
        "table": table,
    })
