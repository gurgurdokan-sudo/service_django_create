from datetime import date
from pathlib import Path
from django.core.files import File
from django.db.models import Sum
from django.utils import timezone
from django.http import FileResponse, HttpResponse

from dashboard.kokuho.exporter import CsvExporter
from dashboard.kokuho.builder import ClaimBuilder
from dashboard.kokuho.validator import ClaimValidator
from dashboard.models import OfficeMonthlyBilling, Office, ServiceMonthlyRecord

import logging
logger = logging.getLogger(__name__)

FILE_NAME = '国保請求'
def create_kokuho_csv(request):
    try:
        year = int(request.GET.get("year"))
        month = int(request.GET.get("month"))
        target_date = date(year, month, 1)
    except (TypeError, ValueError):
        return HttpResponse("請求年月が不正です", status=400)
# 情報が不足していたらエラーで返す
    office = Office.objects.get(pk=1)  # todo request.userからオフィスを取得する

    # Export前にModelを作成
    monthly_records = ServiceMonthlyRecord.objects.filter(
            office=office,
            date__yaer=year,
            date__month=month,
        )
    if not monthly_records.exists(): # ボタン非活性で阻害だが念のため
        return HttpResponse("請求対象の記録がありません", status=400)
    if monthly_records.filter(confirmed=False).exists():
        return HttpResponse("未確定のサービス提供表があります", status=400)

    records = ClaimBuilder(office=office, year=year, month=month).build()
    csv_path = CsvExporter.export(records, year, month)
    
    # ClaimValidatorを修正したら、CSV出力前に有効化する
    # try:
    #     ClaimValidator().validate(records)
    # except ValueError as error:
    #     return HttpResponse(str(error), status=400)

    totals = monthly_records.filter(confirmed=True).aggregate(
        benefit=Sum("benefit_amount"),
        public=Sum("public_amount"),
    )
    total_amount = (totals["benefit"] or 0) + (totals["public"] or 0)

    office_monthly_billing, _ = OfficeMonthlyBilling.objects.update_or_create(
            office=office,
            year=year, month=month,
            defaults={
                'total_amount': total_amount,  # 合計値を設定する
                'csv_generated_at':timezone.now()
                }
        )
    with open(csv_path, "rb") as csv_file:
        billing.kokuhoren_csv.save(
            Path(csv_path).name,
            File(csv_file),
            save=False,
        )

    billing.save()

    return FileResponse(open(csv_path, "rb"), as_attachment=True, filename=f"kokuho_{year}_{month}.csv")
