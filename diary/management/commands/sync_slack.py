"""Slack DMのメッセージを日報に取り込む管理コマンド

使い方:
python manage.py sync_slack --office-id 1 --staff-id 10
python manage.py sync_slack --office-id 1 --staff-id 10 --days 30
python manage.py sync_slack --office-id 1 --staff-id 10 --dry-run
"""
import gzip
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from dashboard.models import Office, UseUser
from diary.models import Entry

CONFIG_PATH = Path(settings.BASE_DIR) / 'slack_config.json'
JST = timezone(timedelta(hours=9))
API_BASE = 'https://slack.com/api/'
TITLE_MAX = 80


class SlackClient:
    """urllib だけで動く最小限のSlack APIクライアント"""

    def __init__(self, token):
        self.token = token

    def call(self, method, **params):
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(
            API_BASE + method,
            data=data,
            headers={
                'Authorization': f'Bearer {self.token}',
                # 大きい応答が途中で切られる環境があるため圧縮して受け取る
                'Accept-Encoding': 'gzip',
            },
        )
        payload = json.loads(self._read_with_retry(req, timeout=30).decode())
        if not payload.get('ok'):
            raise CommandError(
                f'Slack API {method} がエラーを返しました: {payload.get("error")}'
            )
        return payload

    @staticmethod
    def _read_with_retry(req, timeout, attempts=3):
        for attempt in range(1, attempts + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as res:
                    body = res.read()
                    if res.headers.get('Content-Encoding') == 'gzip':
                        body = gzip.decompress(body)
                    return body
            except (http.client.IncompleteRead, urllib.error.URLError, OSError):
                if attempt == attempts:
                    raise
                time.sleep(2 * attempt)

    def download(self, url):
        """url_private からファイルをダウンロードする"""
        req = urllib.request.Request(
            url, headers={'Authorization': f'Bearer {self.token}'}
        )
        return self._read_with_retry(req, timeout=60)


class Command(BaseCommand):
    help = 'Slack DMのメッセージを日報に取り込む'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7,
                            help='何日前まで遡って取得するか（デフォルト: 7）')
        parser.add_argument('--dry-run', action='store_true',
                            help='取り込まずに対象メッセージを表示するだけ')
        parser.add_argument("--office-id", type=int, required=True)
        parser.add_argument("--staff-id", type=int, required=True)

    def handle(self, *args, **options):
        office = Office.objects.filter(pk=options["office_id"]).first()
        if not office:
            raise CommandError("指定した事業所が見つかりません。")

        Staff = get_user_model()
        staff = Staff.objects.filter(
            pk=options["staff_id"],
            office=office,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        ).first()
        if not staff:
            raise CommandError("指定した事業所のスタッフが見つかりません。")
        if not staff.slack_user_id:
            raise CommandError("スタッフにSlackユーザーIDが設定されていません。")

        token = office._slack_bot_token
        if not token:
            raise CommandError("事業所にSlack Botトークンが設定されていません。")

        client = SlackClient(token)
        channel_id = self.open_dm(client, staff.slack_user_id)
        messages = self.fetch_messages(client, channel_id, options["days"])
        targets = [
            m for m in messages
            if m.get('user') == staff.slack_user_id
            and m.get('type') == 'message'
            and not m.get('subtype')
            and (m.get('text', '').strip() or m.get('files'))
            # APIトークン等の機密文字列を含むメッセージは日報にしない
            and not re.search(r'xox[a-z]-[0-9A-Za-z-]+', m.get('text', ''))
        ]

        created = skipped = 0
        for msg in sorted(targets, key=lambda m: m['ts']):
            if Entry.objects.filter(slack_ts=msg['ts']).exists():
                skipped += 1
                continue

            posted_at = datetime.fromtimestamp(float(msg['ts']), tz=JST)
            report_users = list(
                UseUser.objects.filter(
                    assignments__employee=staff,
                    assignments__date=posted_at.date(),
                    assignments__is_daily_reporter=True,
                    monthly_records__office=office,
                    monthly_records__date__year=posted_at.year,
                    monthly_records__date__month=posted_at.month,
                ).distinct()[:2]
            )

            if len(report_users) != 1:
                self.stderr.write(
                    f'スキップ: {posted_at:%Y-%m-%d} の日報担当利用者を'
                    f'一意に特定できません（{len(report_users)}件）'
                )
                skipped += 1
                continue

            report_user = report_users[0]
            text = msg.get('text', '').replace('`', '').strip()
            first_line = text.splitlines()[0] if text else '（画像のみ）'
            title = (first_line[:TITLE_MAX - 1] + '…') if len(first_line) > TITLE_MAX else first_line

            if options['dry_run']:
                self.stdout.write(f'[dry-run] {posted_at:%Y-%m-%d %H:%M} {title}')
                created += 1
                continue

            entry = Entry.objects.create(
                date=report_user,
                title=title,
                body=text or '（Slackから画像を取り込み）',
                slack_ts=msg['ts'],
            )
            self.attach_image(client, entry, msg)
            self.stdout.write(f'取り込み: {posted_at:%Y-%m-%d %H:%M} {title}')
            created += 1

        prefix = '[dry-run] ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}完了: 新規 {created} 件 / 取り込み済みスキップ {skipped} 件'
        ))

    def load_config(self):
        if not CONFIG_PATH.exists():
            raise CommandError(
                f'設定ファイルがありません: {CONFIG_PATH}\n'
                '{"token": "xoxp-...", "user_id": "U...", "channel_id": ""} '
                'の形式で作成してください。'
            )
        config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        for key in ('token', 'user_id'):
            if not config.get(key):
                raise CommandError(f'slack_config.json に {key} を設定してください。')
        return config

    def open_dm(self, client, user_id):
        """user_id とのDMチャンネルを開いてIDを返す"""
        print(client, user_id)
        res = client.call('conversations.open', users=user_id)
        return res['channel']['id']

    def fetch_messages(self, client, channel_id, days):
        oldest = (datetime.now(tz=JST) - timedelta(days=days)).timestamp()
        messages = []
        cursor = None
        while True:
            # 1ページの件数を絞って応答サイズを抑える（大きい応答は途中で切れる環境がある）
            params = {'channel': channel_id, 'oldest': f'{oldest:.6f}', 'limit': 15}
            if cursor:
                params['cursor'] = cursor
            res = client.call('conversations.history', **params)
            messages.extend(res.get('messages', []))
            cursor = res.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
        return messages

    def attach_image(self, client, entry, msg):
        """メッセージ添付の最初の画像をEntryに保存する（失敗しても同期は続行）"""
        for f in msg.get('files', []):
            if not f.get('mimetype', '').startswith('image/'):
                continue
            url = f.get('url_private_download') or f.get('url_private')
            if not url:
                continue
            try:
                data = client.download(url)
                name = f.get('name') or f'slack_{msg["ts"]}.png'
                entry.image.save(name, ContentFile(data), save=True)
            except (urllib.error.URLError, OSError) as e:
                self.stderr.write(f'画像の取得に失敗（スキップ）: {e}')
            break