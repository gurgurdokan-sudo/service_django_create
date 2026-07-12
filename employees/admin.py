from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Assignment, Attendance, Employee


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = ['username', 'last_name', 'first_name', 'slack_user_id', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('従業員情報', {'fields': ('name_kana', 'tel', 'slack_user_id')}),
    )


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'user']
    list_filter = ['date', 'employee']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'kind', 'timestamp']
    list_filter = ['date', 'kind']
