import os
import boto3
from io import BytesIO
from pathlib import Path

from django.conf import settings
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.properties import PageSetupProperties

from dashboard.models.const import SYOKU_ADDONS
import logging
logger = logging.getLogger(__name__)
TEMPLATE_PATH = 'templatesExcel/claim_template.xlsx'

# 明細欄 B10:F19（B:項目 / C:数量 / D:単位 / E:単価 / F:小計）
DETAIL_FIRST_ROW = 10
DETAIL_ROW_COUNT = 10
PRINT_AREA = "A1:G31"

# 単位数（介護報酬）と円を見分ける表示形式。マイナスは▲で表示する。
YEN_FORMAT = '"¥"#,##0;"▲¥"#,##0'
UNIT_FORMAT = '#,##0"単位";"▲"#,##0"単位"'
UNIT_PRICE_FORMAT = '"¥"#,##0.00'
COUNT_FORMAT = '#,##0'


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

    items, subtotal = build_claim_items(summary)
    if len(items) > DETAIL_ROW_COUNT:
        raise ValueError(
            f"明細がテンプレートの{DETAIL_ROW_COUNT}行を超えています（{len(items)}件）。"
        )

    # 提示されたsummaryには税額がないため、税額はsummaryに追加されるまで0扱い。
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
    sheet["F4"] = profile.get("issue_date")

    _write_detail_rows(sheet, items)

    sheet["F20"] = subtotal
    sheet["F21"] = tax
    sheet["F22"] = total
    sheet["C24"] = profile.get("claim_period")
    sheet["C25"] = profile.get("medical_expense_amount")
    # E24:E27は見出しなので、値はF列に書く。
    sheet["F24"] = profile["office_name"]
    sheet["F25"] = profile["office_address"]
    sheet["F26"] = profile.get("office_phone", "")
    sheet["F27"] = profile.get("registration_no", "")
    # お知らせ・備考欄はB30:F30（結合セル）。
    if profile.get("bikou"):
        sheet["B30"] = profile["bikou"]
    _apply_print_setup(sheet)

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


def build_claim_items(summary):
    """請求書の明細行と小計（円）を返す。

    並び：保険内のPlan → 保険内Addon → default_addon → 費用総額（保険給付対象）
    → ▲保険給付額（→ ▲公費負担額 → 支給限度額超過分）→ self_payのAddon
    保険内の明細は単位数、費用総額以降は円で表示する。
    """
    record = summary["record"]
    insurance = summary.get("insurance") or {}
    items = []

    # 保険内のPlan（同一サービスコードはsummaryで集約済み）
    for plan in insurance.get("plans", []):
        count = int(plan.get("actual_count") or 0)
        if count:
            items.append(
                _unit_item(plan["name"], count, plan["unit"], plan["subtotal"])
            )

    # 入浴加算などの保険内Addon（減算はマイナスの単位数のまま表示）
    for addon in insurance.get("addons", []):
        if addon.get("subtotal"):
            items.append(_unit_item(
                addon["name"], addon["count"], addon["unit"], addon["subtotal"]
            ))

    # default_addon（処遇改善加算などの率加算）は月1回として表示
    rate_addon = insurance.get("rate_addon") or {}
    rate_units = int(rate_addon.get("units") or 0)
    if rate_units:
        items.append(_unit_item(rate_addon["name"], 1, rate_units, rate_units))

    total_cost = int(record.get("total_cost") or 0)
    benefit_amount = int(record.get("benefit_amount") or 0)
    public_amount = int(record.get("public_amount") or 0)
    insurance_share = int(record.get("user_share_amount") or 0)
    over_units = int(record.get("over_units") or 0)
    # user_share_amountには支給限度額の超過分（全額自己負担）が含まれる。
    over_cost = insurance_share - (total_cost - benefit_amount - public_amount)
    if over_cost < 0 or bool(over_cost) != bool(over_units):
        raise ValueError("保険分の利用者負担額の内訳が一致しません。")

    if items:
        unit_price_value = insurance.get("unit_price")
        if unit_price_value is None:
            plans = insurance.get("plans") or []
            addons = insurance.get("addons") or []
            rate_addon = insurance.get("rate_addon") or {}
            logger.error(
                "請求書の単価欠落: insurance_keys=%s, plans=%s, addons=%s, default_addon=%s",
                sorted(insurance.keys()),
                [(p.get("code"), p.get("name")) for p in plans],
                [
                    (a.get("code"), a.get("name"), a.get("unit"), a.get("subtotal"))
                    for a in addons
                ],
                {
                    "code": rate_addon.get("code"),
                    "name": rate_addon.get("name"),
                    "units": rate_addon.get("units"),
                },
            )
            raise ValueError(
                "summary['insurance']['unit_price'] がありません。"
                "上のログで保険内の明細・加算を確認してください。"
            )
        unit_price = float(unit_price_value)
        covered_units = int(record.get("within_units") or 0) + rate_units
        items.append(_yen_item(
            "費用総額（保険給付対象）", total_cost,
            covered_units, "単位", unit_price, UNIT_PRICE_FORMAT,
        ))
        items.append(_yen_item("保険給付額", -benefit_amount))
        if public_amount:
            items.append(_yen_item("公費負担額", -public_amount))
        if over_cost:
            items.append(_yen_item(
                "支給限度額超過分（全額自己負担）", over_cost,
                over_units, "単位", unit_price, UNIT_PRICE_FORMAT,
            ))
    elif insurance_share:
        raise ValueError("保険内の明細がないのに利用者負担額があります。")

    # self_payのAddon（昼食代など）
    self_pay = summary.get("self_pay") or {"items": [], "total": 0}
    for item in self_pay.get("items", []):
        if item.get("count"):
            unit = "食" if item["name"] in SYOKU_ADDONS else "回"
            items.append(_yen_item(
                item["name"], item["subtotal"],
                item["count"], unit, item["price"],
            ))

    subtotal = insurance_share + int(self_pay.get("total") or 0)
    return items, subtotal


def _unit_item(name, count, unit, subtotal):
    """保険内の明細。unit・subtotalは円ではなく介護報酬の単位数。"""
    return {
        "name": name,
        "quantity": count,
        "unit": "回",
        "unit_price": unit,
        "subtotal": subtotal,
        "price_format": UNIT_FORMAT,
        "subtotal_format": UNIT_FORMAT,
    }


def _yen_item(name, subtotal, quantity=None, unit="", unit_price=None,
              price_format=YEN_FORMAT):
    return {
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "subtotal": subtotal,
        "price_format": price_format,
        "subtotal_format": YEN_FORMAT,
    }


def _write_detail_rows(sheet, items):
    """B10:F19の明細欄をクリアしてから、明細を上から書き込む。"""
    rows = range(DETAIL_FIRST_ROW, DETAIL_FIRST_ROW + DETAIL_ROW_COUNT)
    for row in rows:
        for column in "BCDEF":
            sheet[f"{column}{row}"].value = None
        # テンプレートの16・18行目は配置が未設定のため、全行でそろえる。
        for column, horizontal in (
            ("C", "center"), ("D", "center"), ("E", "right"), ("F", "right"),
        ):
            sheet[f"{column}{row}"].alignment = Alignment(horizontal=horizontal)

    for row, item in zip(rows, items):
        sheet[f"B{row}"] = item["name"]
        sheet[f"C{row}"] = item["quantity"]
        sheet[f"C{row}"].number_format = COUNT_FORMAT
        sheet[f"D{row}"] = item["unit"]
        sheet[f"E{row}"] = item["unit_price"]
        sheet[f"E{row}"].number_format = item["price_format"]
        sheet[f"F{row}"] = item["subtotal"]
        sheet[f"F{row}"].number_format = item["subtotal_format"]


def _apply_print_setup(sheet):
    """LibreOfficeでPDF化したときにA4縦1ページへ収める。"""
    sheet.print_area = PRINT_AREA
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.orientation = sheet.ORIENTATION_PORTRAIT
    sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1


def get_claim_invoice_path(user, year, month):
    """利用請求書の保存パスを取得するユーティリティ関数。ユーザーIDと年月を指定して、ローカルまたはS3のパスを返す"""
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
        filename = f"利用請求書_{user.name}_{year}_{month}.xlsx"
        return key, filename