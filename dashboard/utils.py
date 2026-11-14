# utils.py
from datetime import date as date_cls
from django.urls import reverse
from dashboard.models import ServicePlan, UseUser
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
logger = logging.getLogger(__name__)

class BreadcrumbUtil:
    @staticmethod
    def create(crumbs_list):
        """
        crumbs_list: [('ラベル', 'URL名' or None, [args]), ...] のリスト
        """
        items = [
            {"label": "利用者一覧", "url": reverse('dashboard:user_list')}
        ]
        for crumb in crumbs_list:
            url_name = None
            args = None
            match crumb:
                case (label, u_name, u_args):
                    url_name = u_name
                    args = u_args
                case (label, u_name):
                    url_name = u_name
                case (label, ):
                    pass
                case _:
                    raise ValueError(f'パンくずの形式が不正です: {crumb}')
            url = reverse(url_name,args=args or []) if url_name else ''
            items.append({"label":label,"url":url})
            
        return json.dumps(items, ensure_ascii=False)

def get_users_scheduled_on(target_date: date_cls, office) -> list[UseUser]:
    """指定した日付に利用予定（schedule_json == '1'）がある利用者のリストを返す"""
    year = target_date.year
    month = target_date.month
    day_str = str(target_date.day)

    plans = ServicePlan.objects.filter(
        monthly_record__office=office,
        year=year, month=month
    ).select_related('user')

    # schedule_json から該当日の予定が '1' のものを抽出し、userを取り出す順序を保持
    scheduled_users = [
        plan.user for plan in plans
        if (plan.schedule_json or {}).get(day_str) == '1'
    ]
    return list(dict.fromkeys(scheduled_users)) # 重複削除

def send_slack_message(office, channel_id, text, blocks=None):
    """指定した事業所の設定を使ってSlackにメッセージを送信する"""
    token = getattr(office, 'slack_bot_token', '')
    if not token:
        logger.warning(f"事業所 {office.name} にSlackトークンが設定されていません。")
        return False

    client = WebClient(token=token)
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=text,
            blocks=blocks
        )
        return True
    except SlackApiError as e:
        logger.error(f"Slack通知エラー: {e.response['error']}")
        return False