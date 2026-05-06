from django.contrib import admin
from .models import User, ServiceMaster, ServicePlan, ServiceRecord, AddOnService, Office, Municipality

admin.site.register(User)
admin.site.register(ServiceMaster)
admin.site.register(ServicePlan)
admin.site.register(ServiceRecord)
admin.site.register(AddOnService)
admin.site.register(Municipality)

@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    readonly_fields = ("id",)