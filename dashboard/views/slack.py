import hashlib
import hmac
import json
import logging
import time
from datetime import date

from django.conf import settings
from django.db import transaction
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from dashboard.models import Office, ServicePlan
from employees.models import Assignment, Staff

logger = logging.getLogger(__name__)


def _valid_slack_signature(request):
    secret = getattr(settings, "SLACK_SIGNING_SECRET", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not secret or not timestamp.isdigit() or not signature:
        return False

    # 古いリクエストの再送を拒否する
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    base = b"v0:" + timestamp.encode() + b":" + request.body
    digest = hmac.new(
        secret.encode(),
        base,
        hashlib.sha256,
    ).hexdigest()
    expected = f"v0={digest}"

    return hmac.compare_digest(expected, signature)


@csrf_exempt
@require_POST
def slack_interactions(request):
    if not _valid_slack_signature(request):
        return HttpResponseForbidden("無効なSlack署名")

    if request.content_type != "application/x-www-form-urlencoded":
        return HttpResponseBadRequest("予期しないcontent type")

    try:
        payload = json.loads(request.POST.get("payload", ""))
    except (json.JSONDecodeError, TypeError):
        return HttpResponseBadRequest("無効なpayload")

    if payload.get("type") != "block_actions":
        return HttpResponseBadRequest("予期しないinteraction type")

    # 「保存」ボタンのアクションだけ受け付ける
    actions = payload.get("actions", [])
    save_action = next(
        (action for action in actions
         if action.get("action_id") == "save_assignments"),
        None,
    )
    if not save_action:
        return HttpResponseBadRequest("保存アクションが見つかりません")

    try:
        target_date = date.fromisoformat(save_action.get("value", ""))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("無効なdate")

    # 今日の通知に対する操作だけ許可
    if target_date != timezone.localdate():
        return HttpResponseForbidden("割り当て日は今日ではありません")

    channel_id = payload.get("channel", {}).get("id")
    actor_slack_id = payload.get("user", {}).get("id")
    if not channel_id or not actor_slack_id:
        return HttpResponseBadRequest("チャンネルまたはユーザーが見つかりません")

    # SlackチャンネルIDから事業所を特定
    office = Office.objects.filter(_slack_channel=channel_id).first()
    if not office:
        return HttpResponseForbidden("channelから事務所が見つかりません")

    # 操作した人が、この事業所に所属する有効なスタッフか確認
    actor_exists = Staff.objects.filter(
        slack_user_id=actor_slack_id,
        office=office,
        is_active=True,
        is_superuser=False,
    ).exists()
    if not actor_exists:
        return HttpResponseForbidden("Staffが事務所で見つかりません")

    state_values = payload.get("state", {}).get("values")
    if not isinstance(state_values, dict):
        return HttpResponseBadRequest("選択された値が不足しています")

    # Block Kitの選択値を検査して集める
    selections = {}
    try:
        for block_id, action_values in state_values.items():
            if not block_id.startswith("user_"):
                continue

            user_id = int(block_id.removeprefix("user_"))
            if user_id <= 0 or user_id in selections:
                return HttpResponseBadRequest("Invalid user block")

            select_action = action_values.get("select_assignees")
            if not select_action:
                return HttpResponseBadRequest("Missing staff selector")

            selected_options = select_action.get("selected_options", [])
            employee_ids = {
                int(option["value"])
                for option in selected_options
            }
            if any(employee_id <= 0 for employee_id in employee_ids):
                return HttpResponseBadRequest("Invalid staff selection")

            selections[user_id] = employee_ids

    except (TypeError, ValueError, KeyError):
        return HttpResponseBadRequest("Invalid selection data")

    if not selections:
        return HttpResponseBadRequest("No users found")

    user_ids = set(selections)

    # 対象利用者が、その事業所の今日の予定に実際に含まれているか確認
    plans = ServicePlan.objects.filter(
        monthly_record__office=office,
        year=target_date.year,
        month=target_date.month,
        user_id__in=user_ids,
    ).only("user_id", "schedule_json")

    scheduled_user_ids = {
        plan.user_id
        for plan in plans
        if (plan.schedule_json or {}).get(str(target_date.day)) == "1"
    }
    if scheduled_user_ids != user_ids:
        return HttpResponseForbidden("User is not scheduled for this office")

    # 選択されたスタッフが全員、同じ事業所の有効な非管理者スタッフか確認
    employee_ids = set().union(*selections.values())
    valid_employee_ids = set(
        Staff.objects.filter(
            id__in=employee_ids,
            office=office,
            is_active=True,
            is_superuser=False,
        ).values_list("id", flat=True)
    )
    if valid_employee_ids != employee_ids:
        return HttpResponseForbidden("Invalid staff selection")

    try:
        # Assignmentの一意制約とget_or_createにより、Slack再送でも二重登録しない
        with transaction.atomic():
            for user_id, selected_employee_ids in selections.items():
                for employee_id in selected_employee_ids:
                    Assignment.objects.get_or_create(
                        employee_id=employee_id,
                        user_id=user_id,
                        date=target_date,
                    )
    except Exception:
        logger.exception("Failed to save Slack assignment")
        return HttpResponse(status=500)

    # Slackには速やかに200を返す
    return HttpResponse(status=200)