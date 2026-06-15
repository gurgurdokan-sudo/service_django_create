import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from dashboard.models import User, Office, Municipality, CareManager, AddOnService
from dashboard.calendar_table import get_month_days
from django.utils import timezone
from django.conf import settings
from django.http import FileResponse
import textwrap

def create_service_sheet(context):
    wb = load_workbook('templatesExcel/service_template.xlsx')

    office = context['office']
    user = context['user']
    year = context['year']
    month = context['month']

    ws = wb['1']
    ws.title = 'スケジュール'
    ws['B2'] = '認定済'
    for i,d in enumerate(office.municipality.municipality_code):
        cell = f'{chr(ord('K')+i)}5'
        ws[cell] = d
    ws['V5'] = office.municipality.name #市町村

    cm = user.care_manager
    ws['Aj5'] = cm.office_name if cm else '' #介護事業所
    ws['Aj6'] = cm.name if cm else '' #介護事業担当者

    now = timezone.now()
    ws['AX5'] = f"{to_nengo(now.year,now.month)} {now.month}月 {now.day}日" #作成年月日
    ws['AX7'] = f"{to_nengo(year,month)} {month}月 1日" #todo届出年月日

    insured_number = str(user.insured_number) #被保険者番号
    print(insured_number,flush=True)
    for i,d in enumerate(insured_number):
        cell = f"{chr(ord('G')+i)}7"
        ws[cell] = d
    ws['V7'] = user.name_kana
    ws['V8'] = user.name
    birth = user.date_of_birth
    ws['G9'] = to_nengo(birth.year,birth.month) #年号を表示
    ws['G11'] = f"{birth.month}月{birth.day}日" #年号以下表示
    ws['N9'] = user.get_gender_display()[:1] #性別一字

    ws['W9'] = user.care_level #介護区分
    if user.old_certificate:
        ws['W11'] = user.old_certificate.care_level #変更前介護区分
        date = user.latest_changed_date
        ws['W12'] = f"{to_nengo(date.year,date.month)} {date.month}月 {date.day}日" #変更日
    ws['AI9'] = user.max_separate_payment #限度額
    ws['BE9'] = '0' #短期入所利用日数 取り敢えず対応しない
#サービス行
    calendar = context['calendar']
    for i,d in enumerate(calendar):
        col = get_column_letter(25 + i)
        ws[f'{col}15'] = d['day']
        ws[f'{col}16'] = d['weekday_jp']
        if d['is_holiday']:
            ws[f'{col}16'] = '◎'
    office_name = office.name.split() #一旦スペース区切り後で、Model項目増やすかも
    row = 17 #strat row
    for plan in context['plans']:
        start = plan.start_time.strftime("%H:%M")
        end = plan.end_time.strftime("%H:%M")
        ws[f'B{row}'] = f'{start}～{end}'
        auto_newline(plan.service_name, ws, f'H{row}')
        ws[f'O{row}'] = office_name[0]
        ws[f'O{row+1}'] = office_name[1]
        for i,c in enumerate(calendar):
            col = get_column_letter(25 + i)
            day = str(c['day'])
            ws[f'{col}{row}'] = plan.schedule_dict.get(day,'')
            ws[f'{col}{row+1}'] = plan.actual_dict.get(day,{}).get('main','')
        ws[f'BD{row}'] = plan.get_total_count('schedule') #total
        ws[f'BD{row+1}'] = plan.get_total_count('actual') #total
        row += 2
    for plan in context['plans']:
        addon = plan.get_addon_summary
        if not addon:
            continue
        for addon_name,days_list in addon.items():
            auto_newline(addon_name, ws, f'H{row}')
            ws[f'O{row}'] = office_name[0]
            ws[f'O{row+1}'] = office_name[1]
            for i,c in enumerate(calendar):
                col = get_column_letter(25 + i)
                day = str(c['day'])
                ws[f'{col}{row}'] = plan.schedule_dict.get(day,'')
                ws[f'{col}{row+1}'] = "1" if day in days_list else ""
            ws[f'BD{row}'] = plan.get_total_count('schedule')
            ws[f'BD{row+1}'] = len(days_list)
            row += 2
    default_service = office.default_service
    if default_service:
        auto_newline(default_service.service_name, ws, f'H{row}')
        ws[f'O{row}'] = office_name[0]
        ws[f'O{row+1}'] = office_name[1]
        ws[f'BD{row}'] = '1' #total
        ws[f'BD{row+1}'] = '1' #total
        row += 2
    ws = wb['2'] #別シート
    ws['AW1'] = f"{to_nengo(now.year,now.month)} {now.month}月 {now.day}日"
    ws['AW2'] = user.name
    ws['AH2'] = insured_number
#請求計算変数
    total_act_price_unit = 0 #合計金額=合計単位
    UNIT_VALUE = float(office.unit_price) #単位数単価(地域区分
    BENEFIT_RATE = user.benefit_rate #給付率
    MAX_PAYMENT= add_comma(user.max_separate_payment) #計算用限度額

    row = 6 #strat row
    for plan in context['plans']:
        ws[f'A{row}'] = office_name[0] + '\n' + office_name[1]
        ws[f'A{row}'].alignment = Alignment(wrap_text=True)
        ws[f'G{row}'] = office.office_number
        auto_newline(plan.service_name,ws,f'L{row}', 6)
        ws[f'Q{row}'] = f'{office.service_type_code}{plan.service_code}'
        ws[f'T{row}'] = plan.unit
        total_act = plan.get_total_count('actual') #回数
        ws[f'Y{row}'] = total_act
        total = int(total_act) * int(plan.unit)
        total_act_price_unit += total
        ws[f'Z{row}'] = add_comma(total) #単位の小計
        ws[f'AC{row}'] = add_comma(total) #本来「種類支給限度額」を適用した後の数値
        row += 1
    for plan in context['plans']:
        if not plan.is_addon:
            continue
        for addon_name, item in context['add_codes'].items():
            ws[f'A{row}'] = office_name[0] + '\n' + office_name[1]
            ws[f'A{row}'].alignment = Alignment(wrap_text=True)
            ws[f'G{row}'] = office.office_number
            auto_newline(addon_name, ws, f'L{row}', 6)
            ws[f'Q{row}'] = f'{office.service_type_code}{item['code']}' if str(item['code']) != '0'  else ''
            ws[f'T{row}'] = item['unit'] #単位数
            ws[f'Y{row}'] = item['count'] #回数
            total = int(item['unit']) * int(item['count'])
            total_act_price_unit += total
            ws[f'Z{row}'] = add_comma(total) if total != 0 else '' #計算
            ws[f'AC{row}'] = add_comma(total) if total != 0 else '' #計算
            row += 1
# 小計計算行
    ws[f'A{row}'] = office_name[0] + '\n' + office_name[1]
    ws[f'A{row}'].alignment = Alignment(wrap_text=True,vertical="center")
    ws[f'G{row}'] = office.office_number
    auto_newline('地域密着通所合計', ws, f'L{row}', 6)

    kako =['(',')']
    ws[f'Z{row}'] = add_comma(total_act_price_unit).join(kako)
    ws[f'AC{row}'] = add_comma(total_act_price_unit).join(kako)
    #ws[f'AF{row}'] = '' #種類支給
    #ws[f'AI{row}'] = '' #種類支給

    ws[f'AO{row}'] = add_comma(total_act_price_unit) #限度内 単位数
    ws[f'AR{row}'] = UNIT_VALUE #単価
    seikyu_taisyu = int(UNIT_VALUE * total_act_price_unit) #切り捨て
    ws[f'AT{row}'] = add_comma(seikyu_taisyu) #費用総額(保険/事業対象
    ws[f'AW{row}'] = int(BENEFIT_RATE*100) #給付率90
    seikyu_bun = int(seikyu_taisyu * BENEFIT_RATE) #切り捨て
    ws[f'AX{row}'] = add_comma(seikyu_bun) #保険/事業費
    ws[f'BA{row}'] = '' #定額利用者負担（通常のデイサービスでは「空欄」
    #↑「単位×地域単価」ではなく、最初から「1回につき500円」があったら利用
    hutan = int(seikyu_taisyu - seikyu_bun)
    ws[f'BD{row}'] = add_comma(hutan) #利用者負担額

#default行
    row += 1
    ws[f'A{row}'] = office_name[0] + '\n' + office_name[1]
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical="center",)
    ws[f'G{row}'] = office.office_number
    auto_newline(default_service.service_name, ws, f'L{row}',6) #default
    RATE = float(default_service.rate)
    default_price_unit = int(total_act_price_unit * RATE)
    ws[f'Z{row}'] = add_comma(default_price_unit).join(kako)
    ws[f'AO{row}'] = add_comma(default_price_unit).join(kako)
    ws[f'AR{row}'] = UNIT_VALUE #単価
    def_seikyu_taisyu = int(default_price_unit * UNIT_VALUE) #切り捨て
    ws[f'AT{row}'] = add_comma(def_seikyu_taisyu) #費用総額(保険/事業対象
    ws[f'AW{row}'] = int(BENEFIT_RATE*100) #給付率90
    AX_seikyu_bun = int(def_seikyu_taisyu * BENEFIT_RATE) #切り捨て
    ws[f'AX{row}'] = add_comma(AX_seikyu_bun) #保険/事業費
    ws[f'BA{row}'] = '' #todo定額利用者負担?
    BD_hutan = int(def_seikyu_taisyu - AX_seikyu_bun)
    ws[f'BD{row}'] = add_comma(BD_hutan) #利用者負担額

# 最終合計
    row = 20
    
    ws[f'Z{row}'] = add_comma(total_act_price_unit) #todo減算ある場合は計算?
    ws[f'AC{row}'] = add_comma(total_act_price_unit)
    ws[f'AF{row}'] = '' #種類（超える
    ws[f'AI{row}'] = '' #種類（限度内

    if total_act_price_unit > MAX_PAYMENT:
        over_units = int(total_act_price_unit)-int(MAX_PAYMENT)
        within_units = MAX_PAYMENT
    else:
        over_units =0
        within_units = total_act_price_unit
    cost_within_limit = int(within_units * UNIT_VALUE) #限度内の単位数 × 地域単価
    insurace_benefit = int(cost_within_limit * BENEFIT_RATE) #費用総額 × 給付率
    user_share_within = cost_within_limit - insurace_benefit #費用総額 － 保険給付額
    user_full_share_over = int(over_units * UNIT_VALUE) # 限度外の単位数 × 地域単価
    ws[f'AL{row}'] = add_comma(over_units) if over_units>0 else ''
    ws[f'AO{row}'] = add_comma(within_units) #単位数
    taisyou = def_seikyu_taisyu + seikyu_taisyu
    ws[f'AT{row}'] = add_comma(taisyou) #費用総額(保険/事業対象
    ws[f'AX{row}'] = add_comma(AX_seikyu_bun + seikyu_bun) #保険/事業費
    ws[f'BD{row}'] = add_comma(BD_hutan + hutan)  #利用者負担額
    ws[f'BG{row}'] = add_comma(user_full_share_over) if over_units>0 else '' #利用者全額負担額(BG)
    ws[f'T{row}'] = add_comma(user.max_separate_payment) #区分支給限度基準額（単位）

    ws.title = '別表（実績）'
    
    filepath = get_service_sheet_path(user, year, month)
    wb.save(filepath)
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)
def to_nengo(year, month=4):
    # 令和
    if (year > 2019) or (year == 2019 and month >= 5):
        return f"令和{year - 2018}年"
    # 平成
    elif (year > 1989) or (year == 1989 and month >= 1):
        return f"平成{year - 1988}年"
    # 昭和
    elif (year > 1926) or (year == 1926 and month >= 12):
        return f"昭和{year - 1925}年"
    # 大正
    elif (year > 1912) or (year == 1912 and month >= 7):
        return f"大正{year - 1911}年"
def auto_newline(text, ws, cell, line=10):
    text = str(text)
    wrapped = "\n".join(textwrap.wrap(text, line))
    ws[cell] = wrapped
    ws[cell].alignment = Alignment(wrap_text=True, vertical="center",)
def add_comma(value):
    return f"{int(value):,}"

def get_service_sheet_path(user, year, month):#Pathを返す
    user_dir = os.path.join(
        settings.MEDIA_ROOT,
        "service_sheets_export",
        f"{user.id}_{user.name}"
    )
    os.makedirs(user_dir, exist_ok=True)

    filename = f"サービス提供表_{user.name}_{year}_{month}.xlsx"
    return os.path.join(user_dir, filename)
