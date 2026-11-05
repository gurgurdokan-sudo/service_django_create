from django.conf import settings
from logging import getLogger
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
def get_office(request):
    user = request.GET.get('user')
    try:
        if user.office:
            return {'office': office}
        else:
            logger.error('Officeが設定されていないユーザ')
            return {'office': None}
    except Exception as e:
        logger.error('Officeが設定されていないユーザ')
        raise ValueError('Officeが設定されていないユーザ')