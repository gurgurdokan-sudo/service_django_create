
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ServicePlan

@api_view(['PATCH'])
def update_schedule(request, plan_id):
    plan = get_object_or_404(ServicePlan, id=plan_id)

    day = request.data.get("day")
    value = request.data.get("value")
    row_type = request.data.get("row_type")  # "schedule" or "actual"

    if row_type == "schedule":
        data = plan.schedule_json
        data[day] = value
        plan.schedule_json = data
    else:
        data = plan.actual_json
        data[day] = value
        plan.actual_json = data

    plan.save()
    return Response({"status": "ok"})
