import logging
from datetime import date

from dashboard.excel.service_calculator import ServiceSheetCalculator
from dashboard.models import ServiceMonthlyRecord

logger = logging.getLogger(__name__)

# Calculator の結果から、そのまま月次記録に保存する項目
RESULT_FIELDS = (
    "total_units",
    "service_units",
    "within_units",
    "over_units",
    "total_cost",
    "benefit_amount",
    "public_amount",
    "user_share_amount",
    "actual_count",
)
RECORD_FIELDS = RESULT_FIELDS

# ------------------------------------------------------------
# 共通ヘルパー
# ------------------------------------------------------------
def _to_int(value):
    """None や Decimal を int にそろえる（JSON で文字列にならないように）"""
    if value in (None, ""):
        return 0
    return int(value)


def _empty_summary():
    return {
        "insurance": {"plans": [], "addons": [], "rate_addon": None},
        "self_pay": {"items": [], "total": 0},
        "record": None,
        "error": None,
    }


def _calc_values(res):
    """Calculator の結果を、月次記録に保存する"""
    return {field: _to_int(res[field]) for field in RESULT_FIELDS}


# ------------------------------------------------------------
# メイン
# ------------------------------------------------------------
def build_service_summary(user, year, month, save=True):
    summary = _empty_summary()

    record = (
        ServiceMonthlyRecord.objects
        .filter(user=user, date=date(year, month, 1))
        .select_related("office")
        .first()
    )
    if record is None:
        return summary

    # まずは DB に保存されている値を入れておく（計算エラー時もこれを返す）
    summary["record"] = record_to_dict(record)

    plans = list(record.plans.all().order_by("id"))

    try:
        res = ServiceSheetCalculator({
            "office": record.office,
            "user": user,
            "plans": plans,
            "dis_year": year,
            "dis_month": month,
        }).get_results()
    except ValueError as e:
        logger.warning("集計できません: record_id=%s, error=%s", record.id, e)
        summary["error"] = str(e)
        return summary

    summary["insurance"] = _insurance_summary(record, plans, res)
    summary["self_pay"] = _self_pay_summary(plans)

    if save:
        apply_results(record, res)
        summary["record"] = record_to_dict(record)
    else:
        # 保存しないときも、計算した値を返す
        summary["record"] = record_to_dict(record, res)

    return summary


# ------------------------------------------------------------
# 保険分
# ------------------------------------------------------------
def _match_plan_items(plans, plan_items):
    """
    プランと計算結果を組み合わせる。
    plan_id があれば ID で、無ければ順番で組み合わせる。
    """
    if plan_items and all("plan_id" in item for item in plan_items):
        by_id = {item["plan_id"]: item for item in plan_items}
        return [(plan, by_id.get(plan.id)) for plan in plans]

    if len(plans) != len(plan_items):
        logger.warning(
            "プラン数と計算結果の数が違います: plans=%s, items=%s",
            len(plans), len(plan_items),
        )
    items = list(plan_items) + [None] * max(0, len(plans) - len(plan_items))
    return list(zip(plans, items))


def _aggregate_plan_rows(plans, plan_items):
    """同じサービスコードのPlanを1行に集約する（時刻は集約条件にしない）。"""
    grouped = {}

    for plan, item in _match_plan_items(plans, plan_items):
        item = item or {}
        code = str(item.get("code") or plan.service_code)
        unit = _to_int(item.get("unit", plan.unit))
        schedule_count = _to_int(plan.get_total_count("schedule"))
        actual_count = _to_int(item.get("count"))
        subtotal_value = item.get("subtotal")
        subtotal = (
            _to_int(subtotal_value)
            if subtotal_value is not None
            else unit * actual_count
        )

        row = grouped.get(code)
        if row is None:
            row = {
                # 代表PlanのIDを残す。
                # 念のため plan_ids に保持する。
                "id": plan.id,
                "plan_ids": [],
                "code": code,
                "name": item.get("name", plan.service_name),
                "unit": unit,
                "schedule_count": 0,
                "actual_count": 0,
                "subtotal": 0,
            }
            grouped[code] = row
        elif row["unit"] != unit:
            # 同一コードの単位数が異なる 想定外
            raise ValueError(
                f"同一サービスコードの単位数が一致しません: {code}"
            )

        row["plan_ids"].append(plan.id)
        row["schedule_count"] += schedule_count
        row["actual_count"] += actual_count
        row["subtotal"] += subtotal

    return sorted(grouped.values(), key=lambda row: row["code"])


def _insurance_summary(record, plans, res):
    # 同一サービスコードの別時間PlanもAPI上で1行にまとめて返す。
    plan_rows = _aggregate_plan_rows(plans, res.get("plan_items", []))

    addons = [
        {
            **item,
            "unit": _to_int(item.get("unit")),
            "count": _to_int(item.get("count")),
            "subtotal": _to_int(item.get("subtotal")),
        }
        for item in res.get("addon_items", [])
    ]

    rate_addon = None
    default = record.office.default_service
    if default:
        rate_addon = {
            "code": f"{record.office.service_type_code}{default.code}",
            "name": default.service_name,
            "rate": str(default.rate),
            "units": _to_int(res.get("def_unit")),
        }
    addon_units = sum(a["subtotal"] for a in addons)
    return {"plans": plan_rows, "addons": addons, "addon_units": addon_units, "rate_addon": rate_addon}


# ------------------------------------------------------------
# 自費分
# ------------------------------------------------------------
def _self_pay_summary(plans):
    items = _self_pay_items(plans)
    return {"items": items, "total": sum(item["subtotal"] for item in items)}


def _self_pay_items(plans):
    items = {}
    for plan in plans:
        for value in plan.get_addon_summary.values():
            addon = value.get("addon")
            if addon is None or addon.insurance_type != "self_pay":
                continue

            item = items.setdefault(addon.id, {
                "id": addon.id,
                "name": addon.service_name,
                "price": _to_int(addon.price),
                "apply_unit": addon.apply_unit,
                "count": 0,
            })
            item["count"] += len(value.get("days") or [])

    for item in items.values():
        # 月額のものは、何日使っても1回
        if item["apply_unit"] == "monthly":
            item["count"] = min(item["count"], 1)
        item["subtotal"] = item["price"] * item["count"]

    return sorted(items.values(), key=lambda item: item["id"])


# ------------------------------------------------------------
# 保存
# ------------------------------------------------------------
def apply_results(record: ServiceMonthlyRecord, res):
    """
    計算結果を月次記録に保存する。
    この関数は「予定・実績が変わったとき」だけ呼ぶ前提なので、
    確定済みなら確定を外す（合計が同じでも、中身が変わっているため）。
    戻り値: 合計の値が変わったかどうか
    """
    new_values = _calc_values(res)
    changed_fields = [
        field for field, value in new_values.items()
        if getattr(record, field) != value
    ]

    for field in changed_fields:
        setattr(record, field, new_values[field])

    update_fields = list(changed_fields)

    if record.confirmed:
        record.confirmed = False
        record.confirmed_at = None
        update_fields += ["confirmed", "confirmed_at"]
        logger.info("確定を解除しました: record_id=%s", record.id)

    if update_fields:
        record.save(update_fields=update_fields)

    return bool(changed_fields)

def record_to_dict(record, res=None):
    data = {field: _to_int(getattr(record, field)) for field in RESULT_FIELDS}
    needs_save = False

    if res is not None:
        calc = _calc_values(res)
        needs_save = any(data[field] != calc[field] for field in RESULT_FIELDS)
        data.update(calc)

    data["confirmed"] = record.confirmed
    data["needs_save"] = needs_save
    return data