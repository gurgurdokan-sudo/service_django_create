from .models import User, ServicePlan, ServiceMaster
from .forms import PlanForm
from .calendar_table import get_month_days
from .excel.service_sheet import create_service_sheet

#Excel出力
def export_service_sheet(request, user_id, year, month):
    user = User.objects.get(id=user_id)
    wb = create_service_sheet(user, year, month)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="【様式】サービス提供票・別表"'

    wb.save(f'サービス提供表_{user.name}_{year}_{month}.xlsx')
    return response