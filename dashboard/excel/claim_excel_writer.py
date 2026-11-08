import os
import boto3
from io import BytesIO
from pathlib import Path

from django.conf import settings
from openpyxl import load_workbook

from dashboard.models.const import SYOKU_ADDONS
import logging
logger = logging.getLogger(__name__)
TEMPLATE_PATH = 'templatesExcel/claim_template.xlsx'

def create_claim_invoice_excel(*, summary, profile, user, year, month):
    """summary.pyの計算結果と表示用プロフィールで請求書Excelを作成する。

    金額はsummaryから取得し、この関数内では再計算しない。
    profileには利用者・事業所など、summaryにない表示項目を渡す。
    """

    record = summary.get("record")
    if record is None:
        raise ValueError("対象月の月次記録がないため請求書を作成できません。")
    if summary.get("error"):
        raise ValueError(f"月次集計に失敗しました: {summary['error']}")

    # summary.pyが保持している確定済みの保険自己負担額・自費明細を使う。
    insurance_share = int(record.get("user_share_amount") or 0)
    self_pay = summary.get("self_pay") or {"items": [], "total": 0}
    self_pay_total = int(self_pay.get("total") or 0)

    # ServiceSummaryPanel.jsxと同様、insurance.plansの実績回数を合算して表示する。
    insurance_plans = (summary.get("insurance") or {}).get("plans", [])
    insurance_actual_count = sum(
        int(plan.get("actual_count") or 0)
        for plan in insurance_plans
    )

    items = []
    if insurance_share:
        items.append({
            "name": "介護保険利用者負担額",
            "quantity": insurance_actual_count,
            "unit": "回",
            # summaryには1回あたりの自己負担額がないため単価は空欄にする。
            "unit_price": None,
            "subtotal": insurance_share,
        })
    for item in self_pay.get("items", []):
        unit = "回"
        name = item["name"]
        if name in SYOKU_ADDONS:
            unit = '食'
        items.append({
            "name": name,
            "quantity": item["count"],
            "unit": unit,
            "unit_price": item["price"],
            "subtotal": item["subtotal"],
        })
    if len(items) > 10:
        raise ValueError(f"明細がテンプレートの10行を超えています（{len(items)}件）。")

    subtotal = insurance_share + self_pay_total
    # todo summaryに追加するまで0扱い。
    tax = int(summary.get("tax") or 0)
    total = subtotal + tax

    workbook = load_workbook(Path(settings.BASE_DIR) / TEMPLATE_PATH)
    sheet = workbook["Sheet1"]

    sheet["B2"] = profile["title"]
    sheet["B3"] = profile["service_name"]
    sheet["B5"] = profile["recipient_name"]
    sheet["B6"] = profile["postal_address"]
    sheet["B7"] = profile.get("user_phone", "")
    sheet["F5"] = total

    # B:項目 / C:数量 / D:単位 / E:単価 / F:小計
    for row in range(10, 16):
        for column in range(2, 7):
            sheet.cell(row=row, column=column).value = None
    for row, item in enumerate(items, start=10):
        sheet.cell(row=row, column=2, value=item["name"])
        sheet.cell(row=row, column=3, value=item["quantity"])
        sheet.cell(row=row, column=4, value=item["unit"])
        sheet.cell(row=row, column=5, value=item["unit_price"])
        sheet.cell(row=row, column=6, value=item["subtotal"])

    sheet["F20"] = subtotal
    sheet["F21"] = tax
    sheet["F22"] = total
    sheet["C24"] = profile.get("payment_terms", "")
    sheet["B26"] = profile.get("bank_account", "")
    sheet["C26"] = profile.get("due_date", "")
    sheet["E24"] = profile["office_name"]
    sheet["E25"] = profile["office_address"]
    sheet["E26"] = profile.get("office_phone", "")
    sheet["E27"] = profile.get("registration_no", "")
    sheet["B28"] = profile.get("bikou", "")

    buffer = BytesIO()
    workbook.save(buffer)
    file_bytes = buffer.getvalue()
    path, filename = get_claim_invoice_path(user, year, month)

    if settings.DJANGO_ENV == "dev":
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(file_bytes)
    else:
        boto3.client("s3").put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=path,
            Body=file_bytes,
            ContentType=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    logger.info("請求書Excelを作成: %s", filename)
    return path, filename
def get_claim_invoice_path(user, year, month):
    """サービス提供表の保存パスを取得するユーティリティ関数ユーザーIDと年月を指定して、ローカルまたはS3のパスを返す"""
    if settings.DJANGO_ENV == 'dev':
        user_dir = os.path.join(
            settings.MEDIA_ROOT,
            # "service_sheets_export",
            f"{user.id}_{user.name}"
        )
        os.makedirs(user_dir, exist_ok=True)
        year_month_dir = f"{year}_{month:02d}"
        date_dir = os.path.join(user_dir, year_month_dir)
        os.makedirs(date_dir, exist_ok=True)
        filename = f"利用請求書_{user.name}_{year}_{month}.xlsx"
        return os.path.join(date_dir, filename), filename
    # s3バージョン
    else:
        key = f"service_sheets_export/{user.id}_{user.name}/{year}_{month:02d}/利用請求書_{user.name}_{year}_{month}.xlsx"
        filename = f"サービス提供表_{user.name}_{year}_{month}.xlsx"
        return key, filename
