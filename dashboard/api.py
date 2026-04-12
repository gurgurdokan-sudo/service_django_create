
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ServicePlan,AddOnService

@api_view(['PATCH'])
def update_schedule(request, plan_id):
    plan = get_object_or_404(ServicePlan, id=plan_id)

    day = request.data.get("day")
    value = request.data.get("value")
    row_type = request.data.get("row_type")  # "schedule" or "actual"
    total = None
    try:
        if row_type == "schedule":
            data = plan.schedule_json
            data[day] = value
            if value == '':
                del data[day]  # 空文字の場合はキーを削除
            plan.schedule_json = data
            # 実績（actual）の main を更新
        elif row_type == "actual_main":
            data = plan.actual_json or {}
            day_data = data.get(day, {"main": "", "addon": []})
            day_data["main"] = value
            data[day] = day_data
            if day_data["main"] == '' and  len(day_data["addon"]) == 0:
                data.pop(day, None)  # main と addon が両方空の場合はキーを削除
            plan.actual_json = data

        # 実績（actual）の addon を追加
        elif row_type == "actual_addon":
            addon = get_object_or_404(AddOnService, id = plan_id)
            data = plan.actual_json or {}
            for d in days:
                day_data = data.get(d, {"main": "", "addon": []})
                if value not in day_data["addon"]:
                    day_data["addon"].append(addon.service_name)
                data[d] = day_data
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
        row_type = row_type.split("_")[0]  # "schedule" または "actual" に変換
        total = plan.get_total_count(row_type)
        print(total,flush=True)
        return Response({"status": "ok","total":total})
    except ServicePlan.DoesNotExist:
        return Response({"status": "error", "message": "ServicePlan not found"}, status=404)

@api_view(['PATCH'])
def create_plan(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    master_id = request.data.get('selected_service', '').split('_')[1]  # "plan_1"
    if master_id:
        master = get_object_or_404(ServiceMaster, id=master_id)
        new_plan = ServicePlan.objects.create(
            user=target_user,
            year="2026", ##todo:動的に
            month="3",
            start_time=request.data.get('start_time'),
            end_time=request.data.get('end_time'),
            service_name=master.service_name,
            service_code=master.service_code,
            unit=master.unit,
        )
        # messages.success(request, "新しいサービスプランが作成されました。")
    else:
        # messages.error(request, "サービスが作成されていません。")
        pass
    return Response({"status": "ok"})