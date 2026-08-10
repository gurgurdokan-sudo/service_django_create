# utils.py
from django.urls import reverse
import json

class BreadcrumbUtil:
    @staticmethod
    def create(crumbs_list):
        """
        crumbs_list: [('ラベル', 'URL名' または None), ...] のリスト
        """
        # 1. 常に「タイトル（ホーム）」を最初に入れる
        items = [
            {"label": "利用者一覧", "url": reverse('dashboard:user_list')}
        ]
        
        # 2. 渡されたリストを順番に追加していく
        for label, url_name in crumbs_list:
            url = reverse(url_name) if url_name else ""
            items.append({"label": label, "url": url})
            
        return json.dumps(items, ensure_ascii=False)