import json
from datetime import date

from employees.models import Assignment


def slack_interactions(request):
    payload = json.loads(request.POST["payload"])

    # 保存ボタンのアクションから日付を取得
    save_action = next(
        a for a in payload["actions"]
        if a["action_id"] == "save_assignments"
    )
    target_date = date.fromisoformat(save_action["value"])

    # 各プルダウンの選択値を取得
    state_values = payload["state"]["values"]

    for block_id, actions in state_values.items():
        if not block_id.startswith("user_"):
            continue

        user_id = int(block_id.removeprefix("user_"))
        selected = actions.get("select_assignees", {}).get("selected_options", [])

        for option in selected:
            employee_id = int(option["value"])
            Assignment.objects.get_or_create(
                employee_id=employee_id,
                user_id=user_id,
                date=target_date,
            )