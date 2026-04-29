from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ServicePlan,AddOnService,User,ServiceMaster

@api_view(['PATCH'])
def update_schedule(request, planId):
    plan = get_object_or_404(ServicePlan, id=planId)
    value = request.data.get("value", "")

    day = request.data.get("day")
    row_type = request.data.get("row_type")  # "schedule" or "actual"
    try:
        #予定を変更
        if row_type == "schedule":
            print(plan.service_name)
            data = plan.schedule_json
            day_data = data.get(day, {"main":"", "addon": {}})
            day_data["main"] == value
            data = day_data
            if value == '':
                del data[day]
            plan.schedule_json = data
            plan.save()
            return Response({"status": "ok"})
        # 実績（actual）の main を更新
        elif row_type == "actual_main":
            data = plan.actual_json or {}
            day_data = data.get(day, {"main": "", "addon": []})
            day_data["main"] = value
            data[day] = day_data
            if day_data["main"] == '' and  len(day_data["addon"]) == 0:
                data.pop(day, None)  # main と addon が両方空の場合はキーを削除
            plan.actual_json = data
            return Response({"status": "ok"})
         # 実績（actual）の addon を追加
        elif row_type == "actual_addon":
            addon_id = str(request.data.get("addon_id"))
            #全autal
            data = plan.actual_json or {}
            day_actual = data.get(day, {"main": "", "addon": {} })
            addon = day_actual.get("addon")
            if addon_id in addon:
                addon.pop(addon_id)
                if not addon :
                    if not actual_addon:
                        data.pop(day,None)
                    else:
                        day_actual["addon"] = {}
                        data[day] =day_actual
                else:
                    day_actual["addon"] =addon
                    data[day]= day_actual
            else:
                addon_obj = get_object_or_404(AddOnService,id= addon_id)
                addon[addon_id] = addon_obj.service_name
                day_actual["addon"] = addon
            plan.actual_json = data
            plan.save()
            return Response({"status": "ok"})
        #実績FULLバージョン
        elif row_type == "actual_full":
            print("actual_fullの処理", flush=True)
            addon_id = str(request.data.get("addon_id"))
            addon_obj = get_object_or_404(AddOnService, id=addon_id)

            days = request.data.get("days", [])
            data = plan.actual_json or {}

            for d in days:
                d = str(d)
                day_data = data.get(d, {"main": "", "addon": {}})
                addon_dict = day_data.get("addon", {})

                addon_dict[addon_id] = addon_obj.service_name

                day_data["addon"] = addon_dict
                data[d] = day_data

            plan.actual_json = data
            plan.save()
            return Response({"status": "ok"})
        # 実績（actual）の addon を削除
        elif row_type == "actual_addon_remove":
            data = plan.actual_json or {}
            addon_name = request.data.get("addon_name")
            target_ids = set()
            for day_info in data.values():
                for addon_id, name in day_info.get("addon").items():
                    if name == addon_name:
                        target_ids.add(addon_id)
            if not target_ids:
                return Response({"status": "ok"})
            for day in list(data.keys()):
                day_data = data.get(str(day), {"main": "", "addon":{}})
                addon_dict = day_data.get("addon",{})
                for aid in target_ids:
                    addon_dict.pop(aid,None)
                if day_data["main"]=="" and len(addon_dict)==0:
                    data.pop(str(day),None)
                else:
                    day_data["addon"] = addon_dict
                    data[str(day)] = day_data
            plan.actual_json = data
            plan.save()
            return Response({"status": "ok"})
        else:
            print("処理error　rowtypeがない", flush=True)
            return Response({"status": "error", "message": "rowtype not found"}, status=404)    
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

@api_view(['DELETE'])
def delete_plan(request, planId):
    try:
        plan = ServicePlan.objects.get(id=planId)
        plan.delete()
        return Response({"status": "ok", "message": f"ServicePlan {planId} deleted"})
    except ServicePlan.DoesNotExist:
        return Response({"status": "error", "message": "ServicePlan not found"}, status=404)