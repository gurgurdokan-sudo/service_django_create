
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ServicePlan

@api_view(['PATCH'])
def update_schedule(request, plan_id):
    plan = get_object_or_404(ServicePlan, id=plan_id)

    day = request.data.get("day")
    value = request.data.get("value")
    row_type = request.data.get("row_type")  # "schedule" or "actual"

    if row_type == "schedule":
        data = plan.schedule_json
        data[day] = value
        plan.schedule_json = data
        # 実績（actual）の main を更新
    elif row_type == "actual_main":
        data = plan.actual_json or {}
        day_data = data.get(day, {"main": "", "addon": []})
        day_data["main"] = value
        data[day] = day_data
        plan.actual_json = data

    # 実績（actual）の addon を追加
    elif row_type == "actual_addon":
        data = plan.actual_json or {}
        day_data = data.get(day, {"main": "", "addon": []})
        if value not in day_data["addon"]:
            day_data["addon"].append(value)
        data[day] = day_data
        plan.actual_json = data

    # 実績（actual）の addon を削除
    elif row_type == "actual_addon_remove":
        data = plan.actual_json or {}
        day_data = data.get(day, {"main": "", "addon": []})
        if value in day_data["addon"]:
            day_data["addon"].remove(value)
        data[day] = day_data
        plan.actual_json = data

    plan.save()
    return Response({"status": "ok"})
