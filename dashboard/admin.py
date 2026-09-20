from django.contrib import admin
from dashboard.models import UseUser, ServiceMaster, ServicePlan, ServiceMonthlyRecord, \
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
@admin.register(UseUser)
class UserAdmin(admin.ModelAdmin):
    readonly_fields = ("id",)