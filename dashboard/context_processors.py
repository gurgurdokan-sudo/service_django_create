from django.conf import settings
from logging import getLogger

from dashboard.models import Office

logger = getLogger(__name__)

from employees.permissions import has_delete_permission

def django_env(request):
    return {"DJANGO_ENV": settings.DJANGO_ENV}

def delete_permission(request):
    return {
        'can_delete': has_delete_permission(request.user)
    }
def vite(request):
    return {'VITE_DEV': getattr(settings, 'VITE_DEV', False)}

def display_office(request):
    office = get_office(request)
    display_name = None

    if office:
        try:
            name_parts = str(office.name or "").split(" ")
            display_name = name_parts[1]
        except IndexError:
            logger.error("事務所名が不正: スペースが含まれていません")
    else:
        logger.warning("事務所が存在しません")

    return {"display_office": display_name}

def get_office(request):
    user = getattr(request, "user", None)
    office = getattr(user, "office", None)

    if office is None:
        logger.warning(
            "リクエストユーザーに事業所が設定されていません: user_id=%s",
            getattr(request.user, "pk", None),
        )
    return office