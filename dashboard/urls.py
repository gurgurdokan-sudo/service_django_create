from django.urls import path
from .views.user_list import user_list
from .views.user_create import user_create
from .views.export_service_sheet import export_service_sheet
from .views.user_detail import user_detail
from .views.user_update import user_update
from .views.user_delete import user_delete
from .views.user_service import user_service
from .views.create_plan import create_plan

from . import api

app_name = 'dashboard'
urlpatterns = [
    path('users/', user_list, name='user_list'),
    path('users/user_create', user_create, name='create'),
    path('users/<int:user_id>/export/<int:year>/<int:month>/', \
     export_service_sheet, name='export_service_sheet'),
    path('user/<int:user_id>/detail/', user_detail, name='detail'),
    path('user/<int:user_id>/edit/', user_update, name='update'),
    path('user/<int:user_id>/delete/', user_delete, name='delete'),
    path('user/<int:user_id>/service/', user_service, name='service'),
    path('user/<int:user_id>/create_plan/', create_plan, name='creatPlan'),
    
# API
    path("api/plan/<int:planId>/update/", api.update_schedule, name="update_schedule"),
    path("api/plan/<int:user_id>/create/", api.create_plan, name="api_create_plan"),
    path("api/plan/<int:planId>/delete/", api.delete_plan, name="api_delete_plan"),
]