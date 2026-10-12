from django.conf import settings
from employees.permissions import has_delete_permission

def django_env(request):
    return {"DJANGO_ENV": settings.DJANGO_ENV}

def delete_permission(request):
    return {
        'can_delete': has_delete_permission(request.user)
    }
def vite(request):
    return {'VITE_DEV': getattr(settings, 'VITE_DEV', False)}