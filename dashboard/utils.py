# utils.py
from django.urls import reverse
import json

class BreadcrumbUtil:
    @staticmethod
    def create(crumbs_list):
        """
        crumbs_list: [('ラベル', 'URL名' or None, [args]), ...] のリスト
        """
        # 常に「タイトル（ホーム）」を最初に入れる
        items = [
            {"label": "利用者一覧", "url": reverse('dashboard:user_list')}
        ]
        
        # 渡されたリストを順番に追加していく
        for label, url_name, args in crumbs_list:
            if url_name:
                url = reverse(url_name,args=args or [])
            else : url =''
            items.append({"label": label, "url": url})
            
        return json.dumps(items, ensure_ascii=False)