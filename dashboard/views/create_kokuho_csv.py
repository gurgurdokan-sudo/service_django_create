import csv
import os
from django.conf import settings
from django.http import FileResponse
from dashboard.models import ServiceMonthlyRecord

def create_kokuho_csv(request):
    year = int(request.GET.get("year"))
    month = int(request.GET.get("month"))

    # CSV生成処理
    csv_path = generate_csv(year, month)

    return FileResponse(open(csv_path, "rb"), as_attachment=True, filename=f"kokuho_{year}_{month}.csv")

def generate_csv(year, month):
    records = ServiceMonthlyRecord.objects.filter(
        confirmed=True,
        date__year=year,
        date__month=month
    ).order_by('-date')

    # CSVファイルの作成
    csv_filename = f"kokuho_{year}_{month}.csv"
    csv_path = os.path.join(settings.MEDIA_ROOT, csv_filename)

    with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        # ヘッダー行の書き込み
        writer.writerow(['User', 'Total Cost', 'Benefit Amount', 'Public Amount', 'User Share Amount'])

        # レコードの書き込み
        for r in records:
            writer.writerow([r.user.name, r.total_cost, r.benefit_amount, r.public_amount, r.user_share_amount])

    return csv_path