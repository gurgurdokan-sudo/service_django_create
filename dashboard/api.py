from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from dashboard.models import ServicePlan, AddOnService, UseUser, ServiceMaster

import logging
logger = logging.getLogger(__name__)

@api_view(["PATCH"])
def update_schedule(request, plan_id):
    plan = get_object_or_404(ServicePlan, id=plan_id)
    value = request.data.get("value", "")

    day = int(request.data.get("day", 1))
    day_key = str(day)

    row_type = request.data.get("row_type")  # "schedule" or "actual"
    try:
        # 編集できない日付なら、保存処理を行わずに終了
        if not plan.can_edit_day(day):
            logger.warning(
                "認定情報切り替え後のため編集できません: "
                "plan_id=%s, day=%s, row_type=%s",
                plan.id,
                day,
                row_type,
            )
            return Response(
                {
                    "status": "error",
                    "message": "認定情報切り替え後のため編集できません",
                },
            )
        # 予定を変更
        if row_type == "schedule":
            total = 0
            logger.info(f"scheduleの処理 {total=}")
            data = plan.schedule_json or {}
            data[day] = value
            plan.schedule_json = data
            plan.save()
            for val in data.values():
                if val == "1":
                    total += 1
            return Response({"status": "ok", "total": total})
        # 実績（actual）の main を更新
        elif row_type == "actual_main":
            logger.info(f"actual_mainの処理{value}")
            total = int(request.data.get("total", 0))
            data = plan.actual_json or {}
            day_data = data.get(day, {"main": "", "addon": {}})
            day_data["main"] = value
            if value == "1":
                total += 1
            else:
                total -= 1
            # main と addon が両方空なら日付ごと削除
            if not day_data["main"] and not day_data["addon"]:
                data.pop(day, None)
            else:
                data[day] = day_data
            plan.actual_json = data
            plan.save()
            return Response({"status": "ok", "total": total})

        # 実績（actual）の addon を更新
        elif row_type == "actual_addon":
            total = int(request.data.get("total", 0))
            logger.info(f"actual_addonの処理 {total=}")
            addon_name = value
            addon_id = str(
                AddOnService.objects.filter(service_name=addon_name)
                .values_list("id", flat=True)
                .first()
            )
            # idから単位を逆引き
            # unit = (
            #     AddOnService.objects.filter(id=addon_id)
            #     .values_list("unit", flat=True)
            #     .first()
            #     or 0
            # )
            # 全autal
            data = plan.actual_json or {}

            day_actual = data.get(day_key, {"main": "", "addon": {}})
            addon = day_actual.get("addon") or {}

            if addon_id in addon:
                logger.info("削除側に入りました")
                addon.pop(addon_id)
                total = max(0, total - 1)
            else:
                logger.info("追加側に入りました")
                addon_obj = get_object_or_404(AddOnService, id=addon_id)
                addon[addon_id] = addon_obj.service_name
                total += 1

            if not addon and not day_actual.get("main"):
                data.pop(day_key, None)
            else:
                day_actual["addon"] = addon
                data[day_key] = day_actual

            plan.actual_json = data
            plan.save()

            return Response({"status": "ok", "total": total})
        # 実績FULLバージョン
        elif row_type == "actual_full":
            logger.info("actual_fullの処理開始")
            schedule_data = plan.schedule_json or {}

            if schedule_data:
                # スケジュールで設定されている日だけを対象にする
                days = [
                    str(day)
                    for day in schedule_data.keys()
                ]
            else:
                days = {
                    str(day)
                    for day in request.data.get("day", [])
                }

            addon_id = request.data.get("addon_id")

            if not addon_id:
                return Response(
                    {"status": "error", "message": "addon_idが指定されていません"},
                )
            # 加算IDを使ってマスタを取得
            addon_obj = get_object_or_404(
                AddOnService,
                id=addon_id,
            )

            actual_data = plan.actual_json or {}

            for day in days:
                day_data = actual_data.get(
                    day,
                    {"main": "", "addon": {}},
                )

                # 既存データを維持しながら加算を追加
                addon_dict = day_data.get("addon") or {}

                # actual_jsonの既存形式を維持
                addon_dict[str(addon_obj.id)] = addon_obj.service_name

                day_data["addon"] = addon_dict
                actual_data[day] = day_data

            plan.actual_json = actual_data
            plan.save(update_fields=["actual_json"])
            logger.info('actual_fullの処理終了')
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
                day_data = data.get(str(day), {"main": "", "addon": {}})
                addon_dict = day_data.get("addon", {})
                for aid in target_ids:
                    addon_dict.pop(aid, None)
                if day_data["main"] == "" and len(addon_dict) == 0:
                    data.pop(str(day), None)
                else:
                    day_data["addon"] = addon_dict
                    data[str(day)] = day_data
            plan.actual_json = data
            plan.save()
            return Response({"status": "ok"})
        else:
            logger.error("処理error rowtypeがない")
            return Response(
                {"status": "error", "message": "rowtype not found"}, status=404
            )
    except ServicePlan.DoesNotExist:
        return Response(
            {"status": "error", "message": "ServicePlan not found"}, status=404
        )


@api_view(["POST"])
def create_plan(request, user_id):
    logger.info(f"{user_id} POSTの呼び出し")
    target_user = get_object_or_404(UseUser, id=user_id)
    messages = f"{target_user.name} のサービスプランを作成します"
    master_id = request.data.get("selected_service", "")  # "1"
    if master_id:
        master = get_object_or_404(ServiceMaster, id=master_id)
        new_plan = ServicePlan.objects.create(
            user = target_user,
            year = int(request.data.get("year")),
            month = int(request.data.get("month")),
            start_time = request.data.get("start_time"),
            end_time = request.data.get("end_time"),
            service_name = master.service_name,
            service_code = master.service_code,
            unit = master.unit,
        )
    else:
        return Response(
            {"status": "error", "message": "invalid selected_service"}, status=400
        )
    return Response({"status": "ok", "message": messages})


@api_view(["DELETE"])
def delete_plan(request, plan_id):
    from employees.permissions import has_delete_permission
    if not has_delete_permission(request.user):
        return Response({"status": "error", "message": "削除権限がありません"}, status=403)
    try:
        plan = ServicePlan.objects.get(id=plan_id)
        plan.delete()
        return Response({"status": "ok", "message": f"ServicePlan {plan_id} deleted"})
    except ServicePlan.DoesNotExist:
        return Response(
            {"status": "error", "message": "ServicePlan not found"}, status=404
        )
