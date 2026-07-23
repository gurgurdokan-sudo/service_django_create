from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Assignment, Attendance, Staff, ShiftPattern


@admin.register(Staff)
class StaffAdmin(UserAdmin):
    list_display = ['username', 'last_name', 'first_name', 'slack_user_id',
                    'can_delete', 'is_active']
    list_filter = UserAdmin.list_filter + ('can_delete',)
    # 削除権限（can_delete）はこの管理サイトからのみ付与・剥奪する
    fieldsets = UserAdmin.fieldsets + (
        ('スタッフ情報', {'fields': ('office', 'name_kana', 'tel', 'slack_user_id')}),
        ('アプリ内権限', {'fields': ('can_delete',)}),
    )


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'user', 'start_time', 'end_time', 'is_daily_reporter']
    list_filter = ['date', 'employee', 'is_daily_reporter']


@admin.register(ShiftPattern)
class ShiftPatternAdmin(admin.ModelAdmin):
    list_display = ['weekday', 'employee', 'user', 'start_time', 'end_time',
                    'is_daily_reporter', 'is_active']
    list_filter = ['weekday', 'is_active']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'kind', 'timestamp']
    list_filter = ['date', 'kind']
