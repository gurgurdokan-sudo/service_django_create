from django.http import FileResponse, HttpResponse

from dashboard.kokuho.exporter import CsvExporter
from dashboard.kokuho.builder import ClaimBuilder
from dashboard.kokuho.validator import ClaimValidator

def create_kokuho_csv(request):
    year = int(request.GET.get("year"))
    month = int(request.GET.get("month"))

    builder = ClaimBuilder()
    records = builder.get_target_users(year, month)
    rows = builder.build_user_claim(records, year, month)

    validator = ClaimValidator()
    try:
        validator.validate(rows)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    headers = [
        "事業所番号",
        "サービス提供年月",
        "保険者番号",
        "被保険者番号",
        "サービス種類",
        "要介護度",
        "サービスコード",
        "サービス提供回数",
        "単位数",
        "単位数単価",
        "請求額",
        "公費",
        "本人負担"
    ]

    exporter = CsvExporter(headers)
    csv_path = exporter.export(rows, year, month)

    return FileResponse(open(csv_path, "rb"), as_attachment=True, filename=f"kokuho_{year}_{month}.csv")
