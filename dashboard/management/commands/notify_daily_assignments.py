from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import Office
from dashboard.utils import get_users_scheduled_on, send_slack_message
from employees.models import Employee


class Command(BaseCommand):
    help = "今日の利用予定をSlackに通知する"

    def handle(self, *args, **options):
        target_date = timezone.localdate()
        sent = 0

        office: Office
        for office in Office.objects.all():
            channel_id = getattr(office, "channel", "")
            if not channel_id:
                continue

            target_users = get_users_scheduled_on(target_date, office)
            text = "\n".join(
                f"・{user} の予定があります" for user in target_users
            ) or "本日の利用予定はありません。"
            staff_members = Employee.objects.all()
            blocks = build_assignment_blocks(target_users, staff_members, target_date)
            resource = send_slack_message(office, channel_id, text, blocks=blocks)
            if resource:
                self.stdout.write(f"通知しました: {office.name}")
                sent += 1
            else:
                self.stderr.write(f"通知に失敗しました: {office.name}")

        self.stdout.write(self.style.SUCCESS(f"完了: {sent}事業所"))

def build_assignment_blocks(target_users, staff_members, target_date):
    staff_options = [
        {
            "text": {
                "type": "plain_text",
                "text": str(staff)[:75],
            },
            "value": str(staff.pk),  # 保存時に使う従業員ID
        }
        for staff in staff_members
    ]

    blocks = [{
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{target_date:%Y年%m月%d日} の担当者を選択",
        },
    }]

    for user in target_users:
        blocks.append({
            "type": "section",
            "block_id": f"user_{user.pk}",  # 利用者IDを保存時に識別
            "text": {
                "type": "mrkdwn",
                "text": f"*{user}*",
            },
            "accessory": {
                "type": "multi_static_select",
                "action_id": "select_assignees",
                "placeholder": {
                    "type": "plain_text",
                    "text": "担当スタッフを選択",
                },
                "options": staff_options,
            },
        })

    blocks.append({
        "type": "actions",
        "elements": [{
            "type": "button",
            "action_id": "save_assignments",
            "value": target_date.isoformat(),
            "text": {"type": "plain_text", "text": "担当を保存"},
            "style": "primary",
        }],
    })
    return blocks