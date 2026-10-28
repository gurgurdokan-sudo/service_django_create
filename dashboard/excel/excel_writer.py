import os
import io
from datetime import date
from django.utils.timezone import now
from django.conf import settings
import boto3
import textwrap
from collections import defaultdict

from openpyxl import load_workbook
from openpyxl.styles import Alignment

from dashboard.excel.service_calculator import ServiceSheetCalculator, format_comma

import logging
logger = logging.getLogger(__name__)


def create_service_sheet(context):
    try:
        wb = load_workbook('templatesExcel/service_template.xlsx')
        calc = ServiceSheetCalculator(context)
        res = calc.get_results()

        user = context['user']
        year, month = context['dis_year'], context['dis_month']
        ws1 = wb['1']  # スケジュール

        # --- Sheet 1: ヘッダー (生活保護情報の印字) ---Sheet1は予定・実績カレンダー用
        if res['is_hogo']:
            pa = res['pa_data']
            ws1['G5'] = "25"  # 法別番号
            ws1['I5'] = pa.hogo_number  # 保護番号(8桁)
            ws1['V9'] = pa.recipient_number  # 受給者番号(10桁)

        # --- Sheet 2: 別表（実績） ---
        ws2 = wb['2']
        current_row = 6
        office_name = context['office'].name.split()[:2]

        # Sheet2 はサービスコード別明細と、必要なサービス種類別集計行を出力する。
        sheet2_rows = build_sheet2_rows(
            res['plan_items'],
            res['addon_items'],
            context['office'],
        )
        for item in sheet2_rows:
            if item['row_type'] == 'service_type_total':
                write_service_type_total(
                    ws2, current_row, item,
                    context['office'].office_number, office_name,
                )
            else:
                write_billing_line(
                    ws2, current_row, item,
                    context['office'].office_number, office_name,
                )
            current_row += 1

        # row 20は既存の最終合計欄として使うため、明細/サービス種類集計がここまで達したら
        if current_row >= 20:
            raise ValueError("Sheet2の明細・集計行が固定合計欄（20行目）に重なります")

        # 小計行 (地域密着通所合計)
        ws2[f'AT{current_row}'] = format_comma(res['total_cost'])  # 10割分
        ws2[f'AX{current_row}'] = format_comma(res['benefit_amount'])  # 保険分(9割)

        # 本人負担欄 (BD列) の制御
        if res['is_hogo']:
            ws2[f'BA{current_row}'] = format_comma(res['public_amount'])  # 公費分(1割)
            ws2[f'BD{current_row}'] = "0"  # 本人は0
        else:
            ws2[f'BD{current_row}'] = format_comma(res['user_share_amount'])  # 本人が払う

        # 最終合計行 (20行目固定)
        ws2['AT20'] = format_comma(res['total_cost'])
        ws2['AX20'] = format_comma(res['benefit_amount'])
        if res['is_hogo']:
            ws2['BA20'] = format_comma(res['public_amount'])
            ws2['BD20'] = "0"
        else:
            ws2['BD20'] = format_comma(res['user_share_amount'])

        # --- 生活保護情報の印字を追加 ---
        bikou_text = ''
        if res['is_hogo']:
            pa = res['pa_data']
            # セル位置はテンプレートに合わせて調整してください
            bikou_text += "生活保護の法別番号:25\n"  # 生活保護の法別番号
            bikou_text += f'公費負担者番号:{pa.hogo_number}\n'  # 公費負担者番号
            bikou_text += f'公費受給者番号:{pa.recipient_number}'  # 公費受給者番号
        ws2['AK23'] = bikou_text
        # ローカル保存処理
        if settings.DJANGO_ENV == 'dev':
            filepath, filename = get_service_sheet_path(user, year, month)
            logger.info("MEDIA_ROOT=%r, file_path=%r, absolute=%r",
                        settings.MEDIA_ROOT, filepath, os.path.abspath(filepath))
            wb.save(filepath)

        # s3の場合保存処理
        else:
            logger.info("s3の処理開始 year=%d, month=%d, 利用者名=%s", year, month, user.username)
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            file_bytes = buffer.getvalue()
            key, filename = get_service_sheet_path(user, year, month)
            upload_service_sheet_to_s3(key, file_bytes)

        # 後処理
        _record_model_update(user, year, month, res)
        return
    except Exception as e:
        logger.error(f"サービス提供表の作成中にエラーが発生しました: {e}")
        raise



SERVICE_TYPE_NAMES = {
    "78": "地域密着型通所介護",
}


def build_sheet2_rows(plan_items, addon_items, office):
    """Sheet2用の明細と、必要なサービス種類別集計行を作る。

    同じ事業所・サービスコード・単位数のPlan/加算は明細1行にまとめる。
    Plan数ではなく、同じ事業所・サービス種類に異なるサービスコードが
    複数ある場合だけ、グループ末尾に集計行を1行作る。
    """
    office_number = str(office.office_number)
    groups = defaultdict(dict)

    for item in [*plan_items, *addon_items]:
        code = str(item["code"])
        unit = int(item["unit"])
        count = int(item.get("count") or 0)
        subtotal = item.get("subtotal")
        subtotal = int(subtotal) if subtotal is not None else unit * count

        # 実績がない明細は出力しない。ただし負の減算単位は残す。
        if count == 0 and subtotal == 0:
            continue

        service_type_code = code[:2]
        group_key = (office_number, service_type_code)
        detail_key = (code, unit)
        details = groups[group_key]

        if detail_key not in details:
            details[detail_key] = {
                "row_type": "detail",
                "name": item["name"],
                "code": code,
                "unit": unit,
                "count": 0,
                "subtotal": 0,
            }

        details[detail_key]["count"] += count
        details[detail_key]["subtotal"] += subtotal

    rows = []
    for (group_office_number, service_type_code), detail_map in sorted(groups.items()):
        details = sorted(
            detail_map.values(),
            key=lambda row: (row["code"], row["unit"]),
        )
        rows.extend(details)

        # 公式記載要領に合わせ、サービス種類内にコードが複数ある場合だけ集計行を出す。
        # 同じコードのPlanが時間帯違いで複数あっても、ここでのコード数は1なので集計行は出ない。
        distinct_service_codes = {row["code"] for row in details}
        if len(distinct_service_codes) > 1:
            service_type_name = SERVICE_TYPE_NAMES.get(
                service_type_code,
                f"サービス種類 {service_type_code}",
            )
            rows.append({
                "row_type": "service_type_total",
                "name": f"{service_type_name} 集計",
                "code": "",
                "unit": "",
                "count": "",
                "subtotal": sum(row["subtotal"] for row in details),
            })

    return rows


def write_service_type_total(ws, row, item, office_number, office_names):
    """サービス種類別の集計行を書く。セル位置は既存write_billing_lineに合わせる。"""
    ws[f'A{row}'] = "\\n".join(office_names)
    ws[f'A{row}'].alignment = Alignment(wrap_text=True)
    ws[f'G{row}'] = office_number
    _auto_newline(item["name"], ws, f'L{row}', 6)
    ws[f'Q{row}'] = ""  # 集計行にサービスコードは書かない
    ws[f'T{row}'] = ""  # 集計行に1回当たりの単位数は書かない
    ws[f'Y{row}'] = ""  # 集計行に回数は書かない
    # 既存の明細出力で単位合計を書いている列に、グループ合計を出す。
    # 実テンプレートで集計値欄の列が異なる場合は、この2列を帳票に合わせる。
    ws[f'Z{row}'] = format_comma(item["subtotal"])
    ws[f'AC{row}'] = format_comma(item["subtotal"])


def write_billing_line(ws, row, item, office_number, office_names):
    """別表の1行分を書き込むヘルパー"""
    ws[f'A{row}'] = "\n".join(office_names)
    ws[f'A{row}'].alignment = Alignment(wrap_text=True)
    ws[f'G{row}'] = office_number
    _auto_newline(item['name'], ws, f'L{row}', 6)
    ws[f'Q{row}'] = item['code']
    ws[f'T{row}'] = item['unit']
    ws[f'Y{row}'] = item['count']
    ws[f'Z{row}'] = format_comma(item['subtotal'])
    ws[f'AC{row}'] = format_comma(item['subtotal'])


def _auto_newline(text, ws, cell, line=10):
    """セル内で自動改行するためのヘルパー"""
    text = str(text)
    wrapped = "\n".join(textwrap.wrap(text, line))
    ws[cell] = wrapped
    ws[cell].alignment = Alignment(wrap_text=True, vertical="center", )


def _record_model_update(user, year, month, res):
    """ServiceMonthlyRecordに計算結果を反映する"""
    from dashboard.models import ServiceMonthlyRecord
    target_date = date(year, month, 1)

    record, _ = ServiceMonthlyRecord.objects.get_or_create(
        user=user,
        date=target_date
    )

    # 計算結果をモデルのフィールドに保存
    record.total_units = res['total_units']  # 10割分
    record.total_cost = res['total_cost']  # 総費用
    record.benefit_amount = res['benefit_amount']  # 保険請求額
    record.public_amount = res['public_amount']  # 公費請求額
    record.user_share_amount = res['user_share_amount']  # 利用者負担額
    record.within_units = res['within_units']  # 10割分の単位数
    record.over_units = res['over_units']  # 超過分の単位数

    # CSV出力用のフィールドも更新
    record.actual_count = res['actual_count']  # 実績日数
    record.service_units = res['service_units']  # サービス＋加算などの単位数合計
    record.addon_units = sum(item['subtotal'] for item in res['addon_items'])  # 加算単位数
    record.claim_units = record.service_units + record.addon_units  # 請求

    record.confirmed = True
    record.confirmed_at = now()
    record.save()
    logger.info(f"{user.name}様の{year}年{month}月分実績を保存しました")


def get_service_sheet_path(user, year, month):
    """サービス提供表の保存パスを取得するユーティリティ関数。ユーザーIDと年月を指定して、ローカルまたはS3のパスを返す。"""
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
        filename = f"サービス提供表_{user.name}_{year}_{month}.xlsx"
        return os.path.join(date_dir, filename), filename
    # s3バージョン
    else:
        key = f"service_sheets_export/{user.id}_{user.name}/{year}_{month:02d}/サービス提供表_{user.name}_{year}_{month}.xlsx"
        filename = f"サービス提供表_{user.name}_{year}_{month}.xlsx"
        return key, filename


def upload_service_sheet_to_s3(key, file_bytes):
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{key}"


def add_comma(value):
    return f"{int(value):,}"