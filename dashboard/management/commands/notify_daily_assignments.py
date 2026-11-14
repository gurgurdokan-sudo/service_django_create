from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import Office
from dashboard.utils import get_users_scheduled_on, send_slack_message


class Command(BaseCommand):
    help = "今日の利用予定をSlackに通知する"

    def handle(self, *args, **options):
        target_date = timezone.localdate()
        sent = 0

        for office in Office.objects.all():
            channel_id = getattr(office, "channel", "")
            if not channel_id:
                continue

            target_users = get_users_scheduled_on(target_date, office)
            text = "\n".join(
                f"・{user} の予定があります" for user in target_users
            ) or "本日の利用予定はありません。"

            if send_slack_message(office, channel_id, text):
                self.stdout.write(f"通知しました: {office.name}")
                sent += 1
            else:
                self.stderr.write(f"通知に失敗しました: {office.name}")

        self.stdout.write(self.style.SUCCESS(f"完了: {sent}事業所"))
    