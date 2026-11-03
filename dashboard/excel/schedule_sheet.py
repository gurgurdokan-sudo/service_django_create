"""Sheet1（スケジュール）：第6表の基本情報と予定・実績カレンダーを書く"""
from openpyxl.utils import get_column_letter

from dashboard.models import AddOnService
from dashboard.models.const import CARE_LEVEL_LIMIT_UNITS
from dashboard.calendar_table import get_month_days, to_wareki_parts, format_wareki_date
from dashboard.excel.service_calculator import format_comma
from dashboard.excel.excel_utils import auto_newline, write_digits

SHEET_TITLE = 'スケジュール'
DAY_ROW = 15  # 日付
WEEKDAY_ROW = 16  # 曜日（祝日は◎）
FIRST_PLAN_ROW = 17  # 予定・実績の1行目
CALENDAR_START_COL = 25  # 1日の列（Y列）


def write_schedule_sheet(ws, user, office, plans, year, month, created_date):
    """Sheet1に基本情報と予定・実績カレンダーを書く"""
    ws.title = SHEET_TITLE
    write_schedule_header(ws, user, office, year, month, created_date)
    write_schedule_calendar(ws, office, plans, year, month)


def write_schedule_header(ws, user, office, year, month, created_date):
    """Sheet1上部の利用者・認定情報（第6表の基本情報欄）を書く"""
    cert, changed_cert = _get_month_certificates(user, year, month)

    # 保険者番号・保険者名
    municipality = office.municipality
    write_digits(ws, 5, 11, municipality.municipality_code, 6)  # K5:P5
    ws['V5'] = municipality.name

    # 居宅介護支援事業者事業所名・担当者名
    care_manager = user.care_manager
    ws['AJ5'] = care_manager.office_name if care_manager else ''
    ws['AJ6'] = care_manager.name if care_manager else ''

    # 作成年月日
    ws['AX5'] = format_wareki_date(created_date)

    # 被保険者番号・フリガナ・被保険者氏名
    write_digits(ws, 7, 7, user.insured_number, 10)  # G7:P7
    ws['V7'] = user.name_kana
    ws['V8'] = user.name

    # 生年月日・性別
    birth_date = user.date_of_birth
    era_name, era_year = to_wareki_parts(birth_date)
    ws['G9'] = f"{era_name}{era_year}年"
    ws['G11'] = f"{birth_date.month}月{birth_date.day}日"
    ws['N9'] = user.get_gender_display()[:1]

    # 要介護状態区分は対象月1日時点の認定を使う（user.care_levelは今日時点）
    ws['W9'] = cert.care_level
    # --- 限度額適用期間 ---
    ws['AT9'] = f"{format_wareki_date(cert.limit_start)}から"
    ws['AT11'] = f"{format_wareki_date(cert.limit_end)}まで"
    # 月途中の区分変更がある月は、限度額が大きい方の限度額を出す
    ws['AI9'] = format_comma(_month_limit_units(cert, changed_cert))
    # 変更後要介護状態区分・変更日（月途中で区分が変わった場合だけ書く）
    if changed_cert and changed_cert.care_level != cert.care_level:
        changed_at = changed_cert.care_level_changed_at or changed_cert.limit_start
        ws['W11'] = changed_cert.care_level
        ws['W12'] = format_wareki_date(changed_at)


def write_schedule_calendar(ws, office, plans, year, month):
    """日付・曜日を書き、Planごとに予定・実績行を続けて書く"""
    office.office_names = (office.name.split() + ["", ""])[:2]
    calendar = get_month_days(year, month)
    _write_calendar_days(ws, calendar)
    columns = _calendar_columns(calendar)

    # 保険対象の加算マスタはPlanごとに変わらないため、ループの前に1回だけ取得する
    insurance_addons = list(
        AddOnService.objects.filter(insurance_type="insurance")
        .values_list("id", "service_name")
    )

    row = FIRST_PLAN_ROW
    for plan in plans:
        row = _write_plan_rows(ws, row, plan, columns, office, insurance_addons)


def _write_calendar_days(ws, calendar):
    """日付（15行目）・曜日（16行目）を書く祝日は曜日欄に◎を出す"""
    for i, calendar_day in enumerate(calendar):
        col = get_column_letter(CALENDAR_START_COL + i)
        ws[f'{col}{DAY_ROW}'] = calendar_day['day']
        ws[f'{col}{WEEKDAY_ROW}'] = (
            '◎' if calendar_day['is_holiday'] else calendar_day['weekday_jp']
        )


def _calendar_columns(calendar):
    """カレンダーの各日を（列記号, 日付の文字列）のリストで返す"""
    return [
        (get_column_letter(CALENDAR_START_COL + i), str(calendar_day['day']))
        for i, calendar_day in enumerate(calendar)
    ]


def _write_plan_rows(ws, row, plan, columns, office, insurance_addons):
    """1つのPlanについて、基本サービスと加算の予定行・実績行を書き、次の行番号を返す"""
    actual_by_day = {
        str(day): value or {}
        for day, value in (plan.actual_dict or {}).items()
    }

    # 基本サービス：予定行と実績行
    ws[f'B{row}'] = f'{plan.start_time:%H:%M}～{plan.end_time:%H:%M}'
    auto_newline(plan.service_name, ws, f'H{row}')
    ws[f'O{row}'] = office.office_names[0]
    ws[f'O{row + 1}'] = office.office_names[1]

    for col, day in columns:
        day_data = actual_by_day.get(day, {})
        ws[f'{col}{row}'] = plan.schedule_dict.get(day, '')
        ws[f'{col}{row + 1}'] = day_data.get('main', '')

    ws[f'BD{row}'] = plan.get_total_count('schedule')
    ws[f'BD{row + 1}'] = plan.get_total_count('actual')
    row += 2

    # Planに紐づく加算：実績がある日をカレンダーに表示
    addon_names = _collect_addon_names(actual_by_day, insurance_addons)
    for addon_key, addon_name in sorted(addon_names.items(), key=lambda item: item[1]):
        auto_newline(addon_name, ws, f'H{row}')
        ws[f'O{row}'] = office.office_names[0]
        ws[f'O{row + 1}'] = office.office_names[1]
        ws[f'B{row}'] = ''
        addon_count = 0

        for col, day in columns:
            addons = (actual_by_day.get(day, {}) or {}).get('addon') or {}
            if isinstance(addons, dict):
                present = addon_key in {str(addon_id) for addon_id in addons}
            else:
                present = addon_name in {str(name) for name in addons}
            ws[f'{col}{row}'] = plan.schedule_dict.get(day, '')  # 予定はPlanと同じ
            ws[f'{col}{row + 1}'] = '1' if present else ''
            addon_count += int(present)

        ws[f'BD{row}'] = plan.get_total_count('schedule')  # 予定の合計回数
        ws[f'BD{row + 1}'] = addon_count
        row += 2

    return row


def _collect_addon_names(actual_by_day, insurance_addons):
    """1か月分の実績から保険対象の加算を集め、{加算IDまたは加算名: 加算名} で返す"""
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
    return addon_names


def _get_month_certificates(user, year, month):
    """対象月1日時点の認定と、月途中から有効になる認定を返す"""
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
    """認定1件分の区分支給限度基準額（単位）を返す"""
    if cert is None: return None
    if cert.limit_amount_type == "任意" and cert.limit_amount_value:
        return int(cert.limit_amount_value)
    return CARE_LEVEL_LIMIT_UNITS.get(cert.care_level)


def _month_limit_units(cert, changed_cert=None):
    """変更前後それぞれの限度額を求め、大きい方を返す"""
    limits = []
    for item in (cert, changed_cert):
        limit = _limit_units(item)
        if limit is not None:
            limits.append(limit)
    return max(limits, default=None)