from django.urls import path
from .views.office_setting import office_setting
from .views.user_views import (
    user_create,
    certificate_create,
    user_list,
    user_detail,
    user_update,
    user_delete,
    )
from .views.export_service_sheet import download_service_sheet, export_excel
from .views.user_service_view import user_service, prev_month_plan, service_act
from .views.create_plan import create_plan
from .views.init_plan import init_plan
from .views.caremana import caremana_list,caremana_update,caremana_delete, caremana_create
from .views.created_service_list import created_service_list

from . import api

app_name = 'dashboard'
urlpatterns = [
    path('office_setting/', office_setting, name='office_setting'),
    path('users/', user_list, name='user_list'),
    path('users/caremana_create', caremana_create, name='caremana_create'),
    path('users/user_create', user_create, name='create'),
    path('user/<int:user_id>/user_create/', certificate_create, name='certificate_create'),
    path('user/<int:user_id>/create_sheet/', export_excel, name='create_sheet'),
    path('user/<int:user_id>/export/', download_service_sheet, name='download_service_sheet'),
    path('user/<int:user_id>/detail/', user_detail, name='detail'),
    path('user/<int:user_id>/edit/', user_update, name='update'),
    path('user/<int:user_id>/delete/', user_delete, name='delete'),
    path('user/<int:user_id>/service/', user_service, name='service'),
    path('user/<int:user_id>/service_prev/', prev_month_plan, name='prevMonthPlan'),
    path('user/<int:user_id>/service_act/',service_act, name='service_act'),
    path('user/<int:user_id>/create_plan/', create_plan, name='createPlan'),
    path('created_service_list/', created_service_list, name='created_service_list'),
    path('caremanagers/', caremana_list, name='caremana_list'),
    path('caremanagers/<int:caremanager_id>/update/', caremana_update, name='caremana_update'),
    path('caremanagers/<int:caremanager_id>/delete/', caremana_delete, name='caremana_delete'),
    path('user/init', init_plan, name='plan'),
    
# API
    path("api/plan/<int:planId>/update/", api.update_schedule, name="update_schedule"),
    path("api/plan/<int:user_id>/create/", api.create_plan, name="api_create_plan"),
    path("api/plan/<int:planId>/delete/", api.delete_plan, name="api_delete_plan"),
]