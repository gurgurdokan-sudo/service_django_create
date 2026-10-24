from typing import Optional, Any
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dashboard.models import (
    AddOnService,
    ServiceMaster,
    ServiceMonthlyRecord,
    ServicePlan,
    UseUser,
)
from dashboard.services.summary import build_service_summary
import logging
logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# 共通ヘルパー
# ------------------------------------------------------------
def _error(message, status=400):
    return Response({"status": "error", "message": message}, status=status)


def _parse_int(value:Any, min_value=None, max_value=None):
    """数字に変換できなければ None を返す"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if min_value is not None and number < min_value:
        return None
    if max_value is not None and number > max_value:
        return None
    return number


def _parse_day(value):
    return _parse_int(value, 1, 31)


def _normalize_keys(data):
    """日付キーを必ず文字列にそろえる（"5" と 5 が混ざらないように）"""
    return {str(key): value for key, value in (data or {}).items()}


def _get_day(data, day_key):
    """1日分の実績データを取り出す（形が崩れていても直す）"""
    day_data = data.get(day_key) or {}
    return {
        "main": day_data.get("main", "") or "",
        "addon": dict(day_data.get("addon") or {}),
    }


def _put_day(data, day_key, day_data):
    """main も addon も空ならその日ごと消す"""
    if not day_data["main"] and not day_data["addon"]:
        data.pop(day_key, None)
    else:
        data[day_key] = day_data


def _count_schedule(data):
    return sum(1 for value in data.values() if value == "1")


def _count_actual(data):
    return sum(1 for day in data.values() if (day or {}).get("main") == "1")


def _count_addon(data, addon_id):
    return sum(
        1 for day in data.values()
        if addon_id in ((day or {}).get("addon") or {})
    )


def _locked(plan, day, row_type):
    logger.warning(
        "認定情報切り替え後のため編集できません: plan_id=%s, day=%s, row_type=%s",
        plan.id, day, row_type,
    )
    return _error("認定情報切り替え後のため編集できません", 409)


def _resolve_addon(request_data, name_key):
    """
    加算を探す。
    addon_id を優先し、無いときだけ名前で探す（同じ名前が複数あればエラー）。
    戻り値: (addon, エラーメッセージ)
    """
    addon_id = request_data.get("addon_id")
    if addon_id not in (None, ""):
        addon_id = _parse_int(addon_id, 1)
        if addon_id is None:
            return None, "addon_id が正しくありません"
        addon = AddOnService.objects.filter(id=addon_id).first()
        return (addon, None) if addon else (None, "加算が見つかりません")

    name = request_data.get(name_key)
    if not name:
        return None, "addon_id が指定されていません"

    addons = list(AddOnService.objects.filter(service_name=name)[:2])
    if not addons:
        return None, "加算が見つかりません"
    if len(addons) > 1:
        return None, "同じ名前の加算が複数あります。addon_id を指定してください"
    return addons[0], None


# ------------------------------------------------------------
# row_type ごとの処理
# 戻り値: Response（エラー） または (変更したか, 追加で返す値)
# ------------------------------------------------------------
def _handle_schedule(request, plan):
    day = _parse_day(request.data.get("day"))
    if day is None:
        return _error("day が正しくありません")
    if not plan.can_edit_day(day):
        return _locked(plan, day, "schedule")

    value = str(request.data.get("value", "") or "")
    day_key = str(day)
    data = _normalize_keys(plan.schedule_json)

    if data.get(day_key, "") == value:
        return False, {"total": _count_schedule(data)}

    if value:
        data[day_key] = value
    else:
        data.pop(day_key, None)

    plan.schedule_json = data
    plan.save()
    return True, {"total": _count_schedule(data)}


def _handle_actual_main(request, plan):
    day = _parse_day(request.data.get("day"))
    if day is None:
        return _error("day が正しくありません")
    if not plan.can_edit_day(day):
        return _locked(plan, day, "actual_main")

    value = str(request.data.get("value", "") or "")
    day_key = str(day)
    data = _normalize_keys(plan.actual_json)
    day_data = _get_day(data, day_key)

    if day_data["main"] == value:
        return False, {"total": _count_actual(data)}

    day_data["main"] = value
    _put_day(data, day_key, day_data)

    plan.actual_json = data
    plan.save()
    return True, {"total": _count_actual(data)}


def _handle_actual_addon(request, plan):
    day = _parse_day(request.data.get("day"))
    if day is None:
        return _error("day が正しくありません")
    if not plan.can_edit_day(day):
        return _locked(plan, day, "actual_addon")

    addon_obj, message = _resolve_addon(request.data, "value")
    if addon_obj is None:
        return _error(message, 404)

    addon_id = str(addon_obj.id)
    day_key = str(day)
    data = _normalize_keys(plan.actual_json)
    day_data = _get_day(data, day_key)

    if addon_id in day_data["addon"]:
        day_data["addon"].pop(addon_id)
    else:
        day_data["addon"][addon_id] = addon_obj.service_name

    _put_day(data, day_key, day_data)

    plan.actual_json = data
    plan.save()
    return True, {"total": _count_addon(data, addon_id), "addon_id": addon_obj.id}


def _handle_actual_full(request, plan):
    addon_obj, message = _resolve_addon(request.data, "addon_name")
    if addon_obj is None:
        return _error(message, 404)

    schedule_data = _normalize_keys(plan.schedule_json)
    if schedule_data:
        # 予定が「1」の日だけ対象（消した日は対象外）
        candidates = [key for key, value in schedule_data.items() if value == "1"]
    else:
        raw_days = request.data.get("days") or request.data.get("day") or []
        if not isinstance(raw_days, (list, tuple)):
            raw_days = [raw_days]
        candidates = [str(d) for d in raw_days]

    target_days, skipped_days = [], []
    for key in candidates:
        day = _parse_day(key)
        if day is None:
            continue
        if plan.can_edit_day(day):
            target_days.append(str(day))
        else:
            skipped_days.append(day)

    addon_id = str(addon_obj.id)
    data = _normalize_keys(plan.actual_json)
    changed = False

    for day_key in target_days:
        day_data = _get_day(data, day_key)
        if addon_id in day_data["addon"]:
            continue
        day_data["addon"][addon_id] = addon_obj.service_name
        _put_day(data, day_key, day_data)
        changed = True

    if changed:
        plan.actual_json = data
        plan.save()

    return changed, {
        "total": _count_addon(data, addon_id),
        "addon_id": addon_obj.id,
        "skipped_days": sorted(skipped_days),
    }


def _handle_actual_addon_remove(request, plan):
    data = _normalize_keys(plan.actual_json)

    addon_id = request.data.get("addon_id")
    if addon_id not in (None, ""):
        target_ids = {str(addon_id)}
    else:
        addon_name = request.data.get("addon_name")
        if not addon_name:
            return _error("addon_id か addon_name を指定してください")
        target_ids = {
            aid
            for day_data in data.values()
            for aid, name in ((day_data or {}).get("addon") or {}).items()
            if name == addon_name
        }

    if not target_ids:
        return False, {}

    changed = False
    for day_key in list(data.keys()):
        day = _parse_day(day_key)
        if day is None or not plan.can_edit_day(day):
            continue
        day_data = _get_day(data, day_key)
        for aid in target_ids:
            if day_data["addon"].pop(aid, None) is not None:
                changed = True
        _put_day(data, day_key, day_data)

    if changed:
        plan.actual_json = data
        plan.save()
    return changed, {}


HANDLERS = {
    "schedule": _handle_schedule,
    "actual_main": _handle_actual_main,
    "actual_addon": _handle_actual_addon,
    "actual_full": _handle_actual_full,
    "actual_addon_remove": _handle_actual_addon_remove,
}


# ------------------------------------------------------------
# API
# ------------------------------------------------------------
@api_view(["PATCH"])
def update_schedule(request, plan_id):
    plan = get_object_or_404(ServicePlan, id=plan_id)

    row_type = request.data.get("row_type")
    handler = HANDLERS.get(row_type)
    if handler is None:
        logger.warning("不明な row_type: plan_id=%s, row_type=%s", plan.id, row_type)
        return _error("row_type が正しくありません")

    monthly_record:ServiceMonthlyRecord = (
        ServiceMonthlyRecord.objects
        .filter(plans=plan)
        .select_related("user")
        .first()
    )
    if monthly_record is None:
        return _error("このプランに対応する月次記録がありません", 409)

    year = monthly_record.date.year
    month = monthly_record.date.month

    with transaction.atomic():
        # 同時に更新されても上書きし合わないようにロック
        plan = ServicePlan.objects.select_for_update().get(id=plan.id)

        result = handler(request, plan)
        if isinstance(result, Response):
            return result

        changed, extra = result
        # 変わったときだけ保存（確定も外れる）
        summary = build_service_summary(
            monthly_record.user, year, month, save=changed,
        )

    logger.info(
        "予定・実績を更新: plan_id=%s, row_type=%s, changed=%s",
        plan.id, row_type, changed,
    )
    return Response({"status": "ok", "changed": changed, "summary": summary, **extra})


@api_view(["POST"])
def create_plan(request, user_id):
    target_user = get_object_or_404(UseUser, id=user_id)

    master_id = _parse_int(request.data.get("selected_service"), 1)
    year = _parse_int(request.data.get("year"), 2000, 2100)
    month = _parse_int(request.data.get("month"), 1, 12)
    start_time = request.data.get("start_time")
    end_time = request.data.get("end_time")

    if master_id is None:
        return _error("サービスが選択されていません")
    if year is None or month is None:
        return _error("年月が正しくありません")
    if not start_time or not end_time:
        return _error("開始時刻と終了時刻を入力してください")

    master = get_object_or_404(ServiceMaster, id=master_id)
    plan = ServicePlan.objects.create(
        user=target_user,
        year=year,
        month=month,
        start_time=start_time,
        end_time=end_time,
        service_name=master.service_name,
        service_code=master.service_code,
        unit=master.unit,
    )
    logger.info("サービスプランを作成: user_id=%s, plan_id=%s", target_user.id, plan.id)
    return Response({
        "status": "ok",
        "plan_id": plan.id,
        "message": f"{target_user.name} のサービスプランを作成しました",
    })


@api_view(["DELETE"])
def delete_plan(request, plan_id):
    from employees.permissions import has_delete_permission

    if not has_delete_permission(request.user):
        return _error("削除権限がありません", 403)

    plan = get_object_or_404(ServicePlan, id=plan_id)
    monthly_record = (
        ServiceMonthlyRecord.objects
        .filter(plans=plan)
        .select_related("user")
        .first()
    )

    with transaction.atomic():
        plan.delete()
        summary = None
        # 消したあとに月の合計を計算し直す
        if monthly_record:
            summary = build_service_summary(
                monthly_record.user,
                monthly_record.date.year,
                monthly_record.date.month,
                save=True,
            )

    logger.info("サービスプランを削除: plan_id=%s", plan_id)
    return Response({
        "status": "ok",
        "message": f"ServicePlan {plan_id} deleted",
        "summary": summary,
    })


@api_view(["GET"])
def service_summary(request, user_id):
    user = get_object_or_404(UseUser, id=user_id)
    year = _parse_int(request.GET.get("year"), 2000, 2100)
    month = _parse_int(request.GET.get("month"), 1, 12)
    if year is None or month is None:
        return _error("year と month を指定してください")

    return Response({
        "status": "ok",
        "summary": build_service_summary(user, year, month, save=False),
    })

@api_view(['GET'])
def validate_monthly_record(request, user_id):
    try:
        year = int(request.GET.get("year",2000))
        month = int(request.GET.get("month",10))
        logger.info(f"{year}{month}")
        if not 1 <= month <= 12:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return JsonResponse({
            "status": "error",
            "errors": ["年・月の指定が不正です。"],
            "warnings": [],
        }, status=400)

    plans:QuerySet[ServicePlan] = ServicePlan.objects.filter(user_id=user_id, year=year, month=month)
    errors = []
    warnings = []

    # --- ヘルパー関数 ---
    def parse_to_int(value:Any, d:int, service_name:str, field_type:str) -> Optional[int]:
        """
        数値を安全にパースする。
        数値化できない不正な文字列の場合はエラーリストに追加し、Noneを返す。
        """
        if value == "" or value is None:
            return 0
        try:
            if isinstance(value, int):
                cunt = value
            elif isinstance(value, float) and value.is_integer():
                cunt = int(value)
            elif isinstance(value, str) and value.strip().isdigit():
                cunt = int(value.strip())
            else:
                raise ValueError
            if cunt < 0:
                raise ValueError
            return cunt
        except (ValueError, TypeError, OverflowError):
            errors.append(
                f"【{service_name}】{d}日: {field_type}に無効な値（{value}）が入力されています。0以上の整数を指定してください。")
            return None

    # --- 月次加算の集計用（利用者・月単位で全体を管理） ---
    global_monthly_addon_counts = {}
    total_actual_main_count = 0

    # 加算ID -> 加算名のマスタ辞書
    global_addons_master = {}

    for plan in plans:
        actual_data = plan.actual_dict
        if not isinstance(actual_data, dict):
            errors.append(f"【{plan.service_name}】: 実績データの形式が不正です。")
            continue

        # --- マスタ取得と存在チェック ---
        addon_ids = set()
        for day, day_info in actual_data.items():
            if not isinstance(day_info, dict):
                errors.append(f"【{plan.service_name}】{day}日: 実績データの形式が不正です。")
                continue
            addon_dict = day_info.get("addon") or {}
            if not isinstance(addon_dict, dict):
                errors.append(f"【{plan.service_name}】{day}日: 加算データの形式が不正です。")
                continue
            addon_ids.update(str(k) for k in addon_dict.keys())

        # このプランで使われている加算をDBから取得
        current_master:dict = {str(a.id): a for a in AddOnService.objects.filter(id__in=addon_ids)}
        global_addons_master.update(current_master)

        # 加算IDのチェック
        for a_id in addon_ids:
            if a_id not in current_master:
                errors.append(f"【{plan.service_name}】: 登録された加算データ（ID: {a_id}）のマスタが見つかりません。")

        # --- 入力チェック ---
        for day, day_info in actual_data.items():
            if not isinstance(day_info, dict):
                continue
            raw_main = day_info.get("main", "")

            main_count = parse_to_int(raw_main, day, plan.service_name, "基本サービス")
            if main_count is not None:
                total_actual_main_count += main_count

            addon_dict = day_info.get("addon") or {}
            if not isinstance(addon_dict, dict):
                continue
            active_addons = []

            for a_id, a_val in addon_dict.items():
                a_id_str = str(a_id)
                if a_val is None or a_val == "":
                    continue
                if not isinstance(a_val, str):
                    errors.append(
                        f"【{plan.service_name}】{day}日: "
                        f"加算（ID:{a_id_str}）のデータ形式が不正です。"
                    )
                    continue
                if not a_val.strip():
                    continue

                active_addons.append(a_id_str)

                # 月額加算のカウントアップ
                addon_obj:AddOnService = current_master.get(a_id_str)
                if addon_obj and addon_obj.apply_unit == "monthly":
                    global_monthly_addon_counts[a_id_str] = global_monthly_addon_counts.get(a_id_str, 0) + 1

            # --- 日ごとに算定する加算だけ、同日の基本サービス実績を確認 ---
            daily_addons = [
                a_id for a_id in active_addons
                if current_master.get(a_id)
                   and current_master[a_id].apply_unit != "monthly"
            ]
            if main_count is not None and main_count <= 0 and daily_addons:
                addon_names = [current_master[k].service_name for k in daily_addons]
                errors.append(
                    f"【{plan.service_name}】{day}日: 基本サービスの実績がないのに加算（{', '.join(addon_names)}）が登録されています。")

        # ---  予定と実績の乖離 ---
        sched_count = plan.get_total_count("schedule")
        act_base_count = plan.count_actual_main_days
        if sched_count != act_base_count:
            warnings.append(
                f"【{plan.service_name}】: 予定{sched_count}回・実績{act_base_count}回です。回数差を確認してください。")


    # ---  月次加算の重複チェック ---
    for a_id, count in global_monthly_addon_counts.items():
        if count > 1:
            addon_name = global_addons_master[a_id].service_name if a_id in global_addons_master else f"ID:{a_id}"
            # 月1回が制度・マスタ仕様で確定している場合は errors.append に変更する。
            warnings.append(
                f"月額算定の加算（{addon_name}）が同月内に複数回（{count}回）登録されています。算定単位を確認してください。")

    # 月額加算は同日に基本サービスがなくてもよいが、月全体で基本実績がない場合は確認を促す。
    if global_monthly_addon_counts and total_actual_main_count == 0:
        warnings.append("月額加算がありますが、月内の基本サービス実績がありません。算定要件を確認してください。")

    # --- 結果の返却 ---
    status = "error" if errors else "warning" if warnings else "ok"
    return JsonResponse({
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "message": "チェックが完了しました。",
    })