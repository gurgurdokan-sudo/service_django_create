from dashboard.models import User, ServicePlan, ServiceMaster

from dashboard.calendar_table import get_month_days
from dashboard.excel.service_sheet import get_service_sheet_path

# Excel ダウンロード（既に作成済みのファイルを返す）
def download_service_sheet(request, user_id, year, month):
    user = User.objects.get(id=user_id)
    file_path = get_service_sheet_path(user, year, month)

    if not os.path.exists(file_path):
        messages.error(request, 'ファイルが作成されていません')
        return redirect('dashboard:user_service', user_id=user_id)

    with open(file_path, 'rb') as f:
        response = HttpResponse(
            f.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
