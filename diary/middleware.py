"""ページを開いたときに裏でSlack同期を走らせるミドルウェア

- 前回の同期から SYNC_INTERVAL 秒以上経っていたらバックグラウンドで実行
- 同期の成否はページ表示に影響させない（失敗はログファイルに記録）
"""
import threading
import time
from pathlib import Path

from django.conf import settings

SYNC_INTERVAL = 10 * 60  # 10分
MARKER = Path(settings.BASE_DIR) / '.last_slack_sync'
LOG = Path(settings.BASE_DIR) / 'slack_sync.log'


def _sync_in_background():
    from django.core.management import call_command
    try:
        with LOG.open('a', encoding='utf-8') as out:
            out.write(f'--- {time.strftime("%Y-%m-%d %H:%M:%S")} 自動同期 ---\n')
            call_command('sync_slack', stdout=out, stderr=out)
    except Exception as e:  # 同期失敗でアプリを止めない
        try:
            with LOG.open('a', encoding='utf-8') as out:
                out.write(f'同期エラー: {e}\n')
        except OSError:
            pass


class SlackAutoSyncMiddleware:
    _lock = threading.Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(('/admin', '/media', '/static')):
            self.maybe_sync()
        return self.get_response(request)

    def maybe_sync(self):
        with self._lock:
            last = MARKER.stat().st_mtime if MARKER.exists() else 0
            if time.time() - last < SYNC_INTERVAL:
                return
            MARKER.touch()  # 先に更新して多重起動を防ぐ
        threading.Thread(target=_sync_in_background, daemon=True).start()
