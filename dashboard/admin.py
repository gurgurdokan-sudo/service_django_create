from django.contrib import admin
from .models import User, ServiceMaster, ServicePlan, ServiceMonthlyRecord, \
    AddOnService, Office, Municipality, CareManager, Certificate, PublicAssistance

admin.site.register(ServiceMaster)
admin.site.register(ServicePlan)
admin.site.register(ServiceMonthlyRecord)
admin.site.register(AddOnService)
admin.site.register(Municipality)
admin.site.register(CareManager)
admin.site.register(Certificate)
admin.site.register(PublicAssistance)


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    readonly_fields = ("id",)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    readonly_fields = ("id",)