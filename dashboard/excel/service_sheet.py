import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from dashboard.models import User, Office, Municipality, CareManager, AddOnService
from dashboard.calendar_table import get_month_days
from dashboard.excel.service_salculator import ServiceSheetCalculator,to_nengo, format_comma
from django.utils import timezone
from django.conf import settings
from django.http import FileResponse
import textwrap
    
import logging
logger = logging.getLogger(__name__)

def create_service_sheet(context):
    wb = load_workbook('templatesExcel/service_template.xlsx')
    calc = ServiceSheetCalculator(context) # 計算実行
    res = calc.results
    
    office = context['office']
    user = context['user']
    year = context['dis_year']
    month = context['dis_month']
    now = timezone.now()

    # --- Sheet 1: スケジュール ---
    ws = wb['1']
    ws.title = 'スケジュール'
    
    # 基本情報
    for i, d in enumerate(office.municipality.municipality_code):
        ws[f'{get_column_letter(11+i)}5'] = d
    ws['V5'] = office.municipality.name
    
    cm = user.care_manager
    ws['Aj5'] = cm.office_name if cm else ''
    ws['Aj6'] = cm.name if cm else ''
    
    ws['AX5'] = f"{to_nengo(now)} {now.month}月 {now.day}日"
    ws['AX7'] = f"{to_nengo(timezone.datetime(year, month, 1))} {month}月 1日"

    # 被保険者情報
    for i, d in enumerate(str(user.insured_number)):
        ws[f"{get_column_letter(7+i)}7"] = d
    ws['V7'], ws['V8'] = user.name_kana, user.name
    ws['G9'] = to_nengo(user.date_of_birth)
    ws['G11'] = f"{user.date_of_birth.month}月{user.date_of_birth.day}日"
    ws['N9'] = user.get_gender_display()[:1]
    ws['W9'] = user.care_level
    ws['AI9'] = format_comma(user.max_separate_payment)

    # サービス実績行の書き込み
    calendar = context['calendar']
    # (カレンダーヘッダー部分は既存通り...)
    
    row = 17
    office_names = (office.name.split() + ["", ""])[:2]
    
    for plan in context['plans']:
        ws[f'B{row}'] = f'{plan.start_time:%H:%M}～{plan.end_time:%H:%M}'
        _auto_newline(plan.service_name, ws, f'H{row}')
        ws[f'O{row}'], ws[f'O{row+1}'] = office_names[0], office_names[1]
        
        for i, c in enumerate(calendar):
            col = get_column_letter(25 + i)
            day = str(c['day'])
            ws[f'{col}{row}'] = plan.schedule_dict.get(day, '')
            ws[f'{col}{row+1}'] = plan.actual_dict.get(day, {}).get('main', '')
        
        ws[f'BD{row}'] = plan.get_total_count('schedule')
        ws[f'BD{row+1}'] = plan.get_total_count('actual')
        row += 2

    # --- Sheet 2: 別表（実績） ---
    ws = wb['2']
    ws.title = '別表（実績）'
    ws['AW1'] = f"{to_nengo(now)} {now.month}月 {now.day}日"
    ws['AW2'], ws['AH2'] = user.name, user.insured_number

    row = 6
    # 明細: プラン
    for item in res['plan_items']:
        _write_billing_row(ws, row, office, item, office_names)
        row += 1
    
    # 明細: 加算
    for item in res['addon_items']:
        _write_billing_row(ws, row, office, item, office_names)
        row += 1

    # 小計（地域密着型通所介護）
    ws[f'A{row}'] = "\n".join(office_names)
    ws[f'G{row}'] = office.office_number
    _auto_newline('地域密着通所合計', ws, f'L{row}', 6)
    ws[f'Z{row}'] = f"({format_comma(res['total_units'])})"
    ws[f'AC{row}'] = f"({format_comma(res['total_units'])})"
    
    # 計算エリア
    ws[f'AO{row}'] = format_comma(res['within_units'])
    ws[f'AR{row}'] = calc.unit_price
    ws[f'AT{row}'] = format_comma(int(res['within_units'] * calc.unit_price))
    ws[f'AW{row}'] = int(res['benefit_rate'] * 100)
    ws[f'AX{row}'] = format_comma(int(res['within_units'] * calc.unit_price * res['benefit_rate']))
    ws[f'BD{row}'] = format_comma(int(res['within_units'] * calc.unit_price * (1 - res['benefit_rate'])))

    # 特定事業所加算（あれば）
    if office.default_service and res['default_service_units'] > 0:
        row += 1
        # ... 同様の書き込みロジック ...

    # 最終合計行 (row=20)
    ws['T20'] = format_comma(res['max_payment'])
    ws['Z20'] = format_comma(res['total_units'])
    ws['AL20'] = format_comma(res['over_units']) if res['over_units'] > 0 else ""
    ws['AO20'] = format_comma(res['within_units'])
    ws['AT20'] = format_comma(res['total_cost'])
    ws['AX20'] = format_comma(res['insurance_benefit'])
    ws['BD20'] = format_comma(res['user_share'])
    ws['BG20'] = format_comma(res['over_cost']) if res['over_cost'] > 0 else ""

    # 保存処理
    filepath, filename = get_service_sheet_path(user, year, month)
    wb.save(filepath)
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)

def _write_billing_row(ws, row, office, item, office_names):
    """別表の1行分を書き込むヘルパー"""
    ws[f'A{row}'] = "\n".join(office_names)
    ws[f'A{row}'].alignment = Alignment(wrap_text=True)
    ws[f'G{row}'] = office.office_number
    _auto_newline(item['name'], ws, f'L{row}', 6)
    ws[f'Q{row}'] = item['code']
    ws[f'T{row}'] = item['unit']
    ws[f'Y{row}'] = item['count']
    ws[f'Z{row}'] = format_comma(item['subtotal'])
    ws[f'AC{row}'] = format_comma(item['subtotal'])

def _auto_newline(text, ws, cell, line=10):
    '''セル内で自動改行するためのヘルパー関数'''
    text = str(text)
    wrapped = "\n".join(textwrap.wrap(text, line))
    ws[cell] = wrapped
    ws[cell].alignment = Alignment(wrap_text=True, vertical="center",)

def get_service_sheet_path(user, year, month):#Pathを返す
    user_dir = os.path.join(
        settings.MEDIA_ROOT,
        "service_sheets_export",
        f"{user.id}_{user.name}"
    )
    os.makedirs(user_dir, exist_ok=True)
    year_month_dir = f"{year}_{month:02d}"
    date_dir = os.path.join(user_dir, year_month_dir)
    os.makedirs(date_dir, exist_ok=True)
    filename = f"サービス提供表_{user.name}_{year}_{month}.xlsx"
    return os.path.join(date_dir, filename), filename