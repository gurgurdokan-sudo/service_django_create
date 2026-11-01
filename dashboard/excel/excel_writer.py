import os
import io
from datetime import date
from django.utils.timezone import localdate, now
from django.conf import settings
import boto3
import textwrap
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from dashboard.models import AddOnService
from dashboard.models.const import CARE_LEVEL_LIMIT_UNITS
from dashboard.calendar_table import get_month_days, to_wareki_parts, format_wareki_date
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
        ws1 = wb['1']
        ws1.title = 'スケジュール'

        # --- Sheet 1: 基本情報（第6表の利用者・認定欄） ---
        created_date = localdate()
        write_schedule_header(
            ws1, user, context['office'], year, month, created_date
        )

        # ---  生活保護情報 ---
        pub = user.get_public_assistance(year, month)
        is_hogo = True if pub else False

        # --- Sheet 1: 予定・実績カレンダー ---
        plans = context['plans']
        office = context['office']
        office.office_names = (office.name.split() + ["", ""])[:2]
        row = 17

        # 日付（15行目）・曜日（16行目）。祝日は曜日欄に◎を出す。
        calendar = get_month_days(year, month)
        for i, calendar_day in enumerate(calendar):
            col = get_column_letter(25 + i)
            ws1[f'{col}15'] = calendar_day['day']
            ws1[f'{col}16'] = (
                '◎' if calendar_day['is_holiday'] else calendar_day['weekday_jp']
            )

        for plan in plans:
            actual_by_day = {
                str(day): value or {}
                for day, value in (plan.actual_dict or {}).items()
            }

            # 基本サービス：予定行と実績行
            ws1[f'B{row}'] = f'{plan.start_time:%H:%M}～{plan.end_time:%H:%M}'
            _auto_newline(plan.service_name, ws1, f'H{row}')
            ws1[f'O{row}'] = office.office_names[0]
            ws1[f'O{row + 1}'] = office.office_names[1]

            for i, calendar_day in enumerate(calendar):
                col = get_column_letter(25 + i)
                day = str(calendar_day['day'])
                day_data = actual_by_day.get(day, {})
                ws1[f'{col}{row}'] = plan.schedule_dict.get(day, '')
                ws1[f'{col}{row + 1}'] = day_data.get('main', '')

            ws1[f'BD{row}'] = plan.get_total_count('schedule')
            ws1[f'BD{row + 1}'] = plan.get_total_count('actual')
            row += 2

            # Planに紐づく加算：実績がある日をカレンダーに表示
            insurance_addons = list(
                AddOnService.objects.filter(insurance_type="insurance")
                .values_list("id", "service_name")
            )
            insurance_addon_ids = {str(addon_id) for addon_id, _ in insurance_addons}
            insurance_addon_names = {str(name) for _, name in insurance_addons}

            addon_names = {}
            for day_data in actual_by_day.values():
                addons = (day_data or {}).get('addon') or {}
                if isinstance(addons, dict):
                    addon_names.update({
                        str(addon_id): str(name)
                        for addon_id, name in addons.items()
                        if str(addon_id) in insurance_addon_ids
                    })
                elif isinstance(addons, (list, tuple, set)):
                    addon_names.update({
                        str(name): str(name)
                        for name in addons
                        if str(name) in insurance_addon_names
                    })

            for addon_key, addon_name in sorted(addon_names.items(), key=lambda item: item[1]):
                _auto_newline(addon_name, ws1, f'H{row}')
                ws1[f'O{row}'] = office.office_names[0]
                ws1[f'O{row + 1}'] = office.office_names[1]
                ws1[f'B{row}'] = ''
                addon_count = 0

                for i, calendar_day in enumerate(calendar):
                    col = get_column_letter(25 + i)
                    day = str(calendar_day['day'])
                    addons = (actual_by_day.get(day, {}) or {}).get('addon') or {}
                    if isinstance(addons, dict):
                        present = addon_key in {str(addon_id) for addon_id in addons}
                    else:
                        present = addon_name in {str(name) for name in addons}
                    ws1[f'{col}{row}'] = plan.schedule_dict.get(day, '')  # 予定はPlanと同じ
                    ws1[f'{col}{row + 1}'] = '1' if present else ''
                    addon_count += int(present)

                ws1[f'BD{row}'] = plan.get_total_count('schedule')  # 予定の合計回数
                ws1[f'BD{row + 1}'] = addon_count
                row += 2

        # --- Sheet 2: 別表（実績） ---
        ws2 = wb['2']
        ws2.title = '別表（実績）'
        ws2['AW1'] = f"{created_date.year}年{created_date.month}月{created_date.day}日"
        ws2['AH2'] = user.insured_number
        ws2['AW2'] = user.name
        current_row = 6
        office.simple_name = office.name.split()[:2]

        # Sheet2はPlan・加算の明細を出し、全体集計とデフォルト加算を続ける。
        detail_rows = build_sheet2_rows(
            res['plan_items'],
            res['addon_items'],
            office,
        )
        detail_rows = calc.apply_detail_amounts(
            detail_rows, res['within_units']
        )
        for item in detail_rows:
            item['is_subtotal'] = False
            write_billing_line(
                ws2, current_row, item, office
            )
            current_row += 1

        # Plan・加算の集計は1行だけ出し、単位数を括弧で囲む。
        if detail_rows:
            summary_item = {
                'name': '地域密着通所合計',
                'subtotal': sum(int(item.get('subtotal') or 0) for item in detail_rows),
                'cost_total': sum(int(item.get('cost_total') or 0) for item in detail_rows),
                'benefit_rate': calc.benefit_rate,
                'benefit_amount': sum(int(item.get('benefit_amount') or 0) for item in detail_rows),
                'public_amount': sum(int(item.get('public_amount') or 0) for item in detail_rows),
                'user_share_amount': sum(int(item.get('user_share_amount') or 0) for item in detail_rows),
                'parenthesize_subtotal': True,
                'within_units': res['within_units'],
            }
            write_service_type_total(
                ws2, current_row, summary_item,context['office'],
            )
            current_row += 1

        # 集計行の直下にデフォルト加算（処遇改善加算）を出す。
        default_service = context['office'].default_service
        default_units = int(res.get('def_unit') or 0)
        if default_service and default_units > 0:
            default_cost = int(res.get('def_total_cost') or 0)
            default_benefit = int(default_cost * calc.benefit_rate)
            default_share = 0 if is_hogo else default_cost - default_benefit
            default_public = default_cost - default_benefit if is_hogo else 0
            default_item = {
                'name': default_service.service_name,
                'code': f"{context['office'].service_type_code}{default_service.code}",
                'unit': '',
                'count': '',
                'subtotal': default_units,
                'cost_total': default_cost,
                'benefit_rate': calc.benefit_rate,
                'benefit_amount': default_benefit,
                'public_amount': default_public,
                'user_share_amount': default_share,
                'parenthesize_subtotal': True,
                'is_subtotal': True,
                'is_default': True,
                'within_units': res['within_units'],
            }
            write_billing_line(
                ws2, current_row, default_item, office
            )
            current_row += 1

        # row 20は既存の最終合計欄として使うため、明細/サービス種類集計がここまで達したら
        if current_row >= 20:
            raise ValueError("Sheet2の明細・集計行が固定合計欄（20行目）に重なります")

        # 費用総額・保険給付額・利用者負担は各明細行に出力済み。
        # 明細の直後に合計金額を重ねて書くと二重計上になるため、全体合計は20行目だけに出す。

        # 最終合計行 (20行目固定)
        ws2['AT20'] = format_comma(res['total_cost'])
        ws2['AX20'] = format_comma(res['benefit_amount'])
        # if is_hogo:
        #     ws2['BD20'] = format_comma(res['public_amount'])
        #     ws2['BG20'] = "0"
        # else:
        ws2['BG20'] = format_comma(res['user_share_amount'])

        # --- 生活保護情報の印字を追加 ---
        bikou_text = []
        if is_hogo:
            bikou_text.extend([
                "生活保護の法別番号:25 ",  # 生活保護の法別番号
                f"公費負担者番号:{pub.hogo_number} ",  # 公費負担者番号
                f"公費受給者番号:{pub.recipient_number}", # 公費受給者番号
            ])
        for i, text in enumerate(bikou_text, start=0):
            ws2[f'AK{23 + i}'] = text
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



def build_sheet2_rows(plan_items, addon_items, office):
    """Plan・加算を個別明細のまま返し、集計は呼び出し元で1行だけ作る。"""
    rows = []
    for item in [*plan_items, *addon_items]:
        row = dict(item)
        unit = int(row.get("unit") or 0)
        count = int(row.get("count") or 0)
        subtotal = row.get("subtotal")
        subtotal = int(subtotal) if subtotal is not None else unit * count

        # 実績がない明細は出力しない。ただし負の減算単位は残す。
        if count == 0 and subtotal == 0:
            continue

        row["row_type"] = "detail"
        row["unit"] = unit
        row["count"] = count
        row["subtotal"] = subtotal
        rows.append(row)

    return rows


def write_service_type_total(ws, row, item, office):
    """Plan・加算の集計行を書く。単位数を括弧で囲み、金額欄も出力する。"""
    total_item = dict(item)
    total_item.update({
        "code": "",
        "unit": "",
        "count": "",
        "parenthesize_subtotal": True,
        "is_subtotal": True,
    })
    write_billing_line(ws, row, total_item, office)


def write_billing_line(ws, row, item, office):
    """別表の1行分を書き込むヘルパー"""
    ws[f'A{row}'] = "\n".join(office.simple_name)
    ws[f'A{row}'].alignment = Alignment(wrap_text=True)
    ws[f'G{row}'] = office.office_number
    _auto_newline(item['name'], ws, f'L{row}', 6)
    ws[f'Q{row}'] = item['code']
    ws[f'T{row}'] = item['unit']
    ws[f'Y{row}'] = item['count']
    subtotal_text = format_comma(item.get('subtotal'),9999)
    if item.get('parenthesize_subtotal'):
        subtotal_text = f'({subtotal_text})'
    ws[f'Z{row}'] = subtotal_text
    ws[f'AC{row}'] = subtotal_text

    # 費用総額・給付率・保険給付額・利用者負担
    if item.get('is_subtotal', False):
        if item.get('is_default', False):
            units = item.get('subtotal')
            units_text = f"({format_comma(units)})" if units is not None else ""
        else:
            units = item.get('within_units')
            units_text = format_comma(units) if units is not None else ""

        # 区分支給 限度基準内 単位数
        ws[f'AO{row}'] = units_text
        ws[f'AR{row}'] = office.unit_price
        ws[f'AT{row}'] = format_comma(item.get('cost_total'))
        benefit_rate = float(item.get('benefit_rate') or 0)
        ws[f'AW{row}'] = int(benefit_rate * 100) if benefit_rate else ''
        ws[f'AX{row}'] = format_comma(item.get('benefit_amount'))
        ws[f'BG{row}'] = format_comma(item.get('user_share_amount'))

def write_schedule_header(ws, user, office, year, month, created_date):
    """Sheet1上部の利用者・認定情報（第6表の基本情報欄）を書く。"""
    cert, changed_cert = _get_month_certificates(user, year, month)

    # 保険者番号・保険者名
    municipality = office.municipality
    _write_digits(ws, 5, 11, municipality.municipality_code, 6)  # K5:P5
    ws['V5'] = municipality.name

    # 居宅介護支援事業者事業所名・担当者名
    care_manager = user.care_manager
    ws['AJ5'] = care_manager.office_name if care_manager else ''
    ws['AJ6'] = care_manager.name if care_manager else ''

    # 作成年月日
    ws['AX5'] = format_wareki_date(created_date)

    # 被保険者番号・フリガナ・被保険者氏名
    _write_digits(ws, 7, 7, user.insured_number, 10)  # G7:P7
    ws['V7'] = user.name_kana
    ws['V8'] = user.name

    # 生年月日・性別
    birth_date = user.date_of_birth
    era_name, era_year = to_wareki_parts(birth_date)
    ws['G9'] = f"{era_name}{era_year}年"
    ws['G11'] = f"{birth_date.month}月{birth_date.day}日"
    ws['N9'] = user.get_gender_display()[:1]

    # 要介護状態区分は対象月1日時点の認定を使う（user.care_levelは今日時点）。
    ws['W9'] = cert.care_level
    # --- 限度額適用期間 ---
    ws['AT9'] = f"{format_wareki_date(cert.limit_start)}から"
    ws['AT11'] = f"{format_wareki_date(cert.limit_end)}まで"
    # 月途中の区分変更がある月は、限度額が大きい方の限度額を出す。
    ws['AI9'] = format_comma(_month_limit_units(cert, changed_cert))
    # 変更後要介護状態区分・変更日（月途中で区分が変わった場合だけ書く）
    if changed_cert and changed_cert.care_level != cert.care_level:
        changed_at = changed_cert.care_level_changed_at or changed_cert.limit_start
        ws['W11'] = changed_cert.care_level
        ws['W12'] = format_wareki_date(changed_at)

def _get_month_certificates(user, year, month):
    """対象月1日時点の認定と、月途中から有効になる認定を返す。"""
    cert = user.get_certificate(year, month)
    if cert is None:
        raise ValueError(f"{year}年{month}月の認定情報がありません")

    changed_cert = user.latest_changed_cert(year, month)
    if (
        changed_cert is None
        or changed_cert.pk == cert.pk
        or changed_cert.limit_start.day == 1
    ):
        changed_cert = None
    return cert, changed_cert


def _limit_units(cert):
    """認定1件分の区分支給限度基準額（単位）を返す。"""
    if cert.limit_amount_type == "任意" and cert.limit_amount_value:
        return int(cert.limit_amount_value)
    return CARE_LEVEL_LIMIT_UNITS.get(cert.care_level)


def _month_limit_units(cert, changed_cert=None):
    limits = [
        _limit_units(item)
        for item in (cert, changed_cert)
        if item is not None
    ]
    limits = [value for value in limits if value is not None]
    return max(limits) if limits else None


def _write_digits(ws, row, start_col, value, length):
    """番号を1マス1文字で書く。桁数違いは帳票の欄ずれになるためエラーにする。"""
    text = str(value or "").strip()
    if len(text) != length:
        raise ValueError(f"{length}桁の番号を設定してください: {text!r}")
    for i, char in enumerate(text):
        ws[f"{get_column_letter(start_col + i)}{row}"] = char

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