from django.utils import timezone

from dashboard.models import Office
from dashboard.utils import get_users_scheduled_on, send_slack_message

def notify_daily_assignments():
    office = Office.objects.get(pk=1) # todo 後で取得方法考える
    target_date = timezone.localdate()
    target_users = get_users_scheduled_on(target_date, office)
    token = office.token
    # 通知先チャンネルID
    channel = office.channel
    messages = ''
    for target_user in target_users:
        messages = messages + f'{target_user}の予定があります'
    send_slack_message(token, channel, messages)