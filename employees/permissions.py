'''削除権限（can_delete）の判定と保護デコレーター

- superuser または can_delete=True のスタッフだけが削除操作を実行できる
- 権限が無い場合は 403（templates/403.html）を表示する
- can_delete の付与・剥奪は Django 管理サイトからのみ行う（画面のフォームには出さない）
'''
from functools import wraps

from django.core.exceptions import PermissionDenied


def has_delete_permission(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'can_delete', False)
    )


def delete_permission_required(view_func):
    '''関数ベースの削除ビューに付けるデコレーター'''
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not has_delete_permission(request.user):
            raise PermissionDenied('削除権限がありません')
        return view_func(request, *args, **kwargs)
    return wrapper
