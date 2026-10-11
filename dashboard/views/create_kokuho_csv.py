from django.http import FileResponse, HttpResponse

from dashboard.kokuho.exporter import CsvExporter
from dashboard.kokuho.builder import ClaimBuilder
from dashboard.kokuho.validator import ClaimValidator
import logging

from dashboard.models import Office

logger = logging.getLogger(__name__)

def create_kokuho_csv(request):
    year = int(request.GET.get("year"))
    month = int(request.GET.get("month"))
# 情報が不足していたらエラーで返す
    builder = ClaimBuilder(office=Office.objects.get(pk=1),year=year,month=month)
    records = builder.build()

    # validator = ClaimValidator()
    # try:
    #     logger.info("CSV export started")
    #     validator.validate(rows)
    # except ValueError as e:
    #     logger.error("Validation failed: %s", e)
    #     return HttpResponse(str(e), status=400)

    csv_path = CsvExporter().export(records, year, month)

    return FileResponse(open(csv_path, "rb"), as_attachment=True, filename=f"kokuho_{year}_{month}.csv")
