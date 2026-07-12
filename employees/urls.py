from django.urls import path

from . import views

app_name = 'employees'
urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('create/', views.employee_create, name='employee_create'),
    path('<int:employee_id>/edit/', views.employee_update, name='employee_update'),
    path('<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),

    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/create/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:assignment_id>/delete/', views.assignment_delete, name='assignment_delete'),

    path('attendances/', views.attendance_list, name='attendance_list'),
]
