
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ServicePlan,AddOnService,User,ServiceMaster

@api_view(['PATCH'])
def update_schedule(request, user_id):
    plan_id = request.data.get("plan_id")
    plan = get_object_or_404(ServicePlan, id=plan_id)
    value = request.data.get("value", "")

    day = request.data.get("day")
    row_type = request.data.get("row_type")  # "schedule" or "actual"
    total = None
    try:
        if row_type == "schedule":
            print(plan.service_name)
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
            print('------------actual_addon------------',flush=True)
            data = plan.actual_json or {}
            day_data = data.get(day, {"main": "", "addon": []})
            if value in day_data["addon"]:
                day_data["addon"].remove(value)
            else:
                day_data["addon"].append(value)
            data[day] = day_data
            if day_data["main"] == '' and len(day_data["addon"])== 0:
                data.pop(day,None)
            plan.actual_json = data
            

        # 実績（actual）の addon を削除
        elif row_type == "actual_addon_remove":
            data = plan.actual_json or {}
            day_data = data.get(day, {"main": "", "addon": []})
            if day=='all':
                for i,data in enumerate(day_data):
                    if data in "addon":
                        day_data["addon"].remove(value)
            elif value in day_data["addon"]:
                day_data["addon"].remove(value)
            data[day] = day_data
            plan.actual_json = data
        plan.save()
        row_type = row_type.split("_")[0]  # "schedule" または "actual" に変換
        total = plan.get_total_count(row_type)
        print('トータルを更新',total,flush=True)
        return Response({"status": "ok","total":total})
    except ServicePlan.DoesNotExist:
        return Response({"status": "error", "message": "ServicePlan not found"}, status=404)

@api_view(['POST'])
def create_plan(request, user_id):
    print(user_id,"POSTの呼び出し",flush=True)
    target_user = get_object_or_404(User, id=user_id)
    messages = f'APIでユーザーID {target_user.name} のサービスプランを作成する処理が呼び出されました。'
    master_id = request.data.get('selected_service', '')  # "1"
    if master_id:
        pass
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
    else:
        return Response({"status": "error", "message": "invalid selected_service"}, status=400)
    return Response({"status": "ok", "message": messages})
