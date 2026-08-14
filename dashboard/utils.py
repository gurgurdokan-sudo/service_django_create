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