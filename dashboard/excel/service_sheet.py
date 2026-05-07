from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from dashboard.models import User, Office, Municipality, CareManager
from django.utils import timezone
from dashboard.calendar_table import get_month_days

def create_service_sheet(context):
    wb = load_workbook('templatesExcel/service_template.xlsx')
    ws = wb['1']
    ws.title = 'スケジュール'
    ws['B2'] = '認定済'
    office = context['office']
    user = context['user']
    for i,d in enumerate(office.municipality.municipality_code):
        cell = f'{chr(ord('K')+i)}5'
        ws[cell] = d
    ws['V5'] = office.municipality.name #市町村

    cm = user.care_manager
    ws['Aj5'] = cm.office_name if cm else '' #介護事業所
    ws['Aj6'] = cm.name if cm else '' #介護事業担当者

    now = timezone.now()
    ws['AX5'] = f"{to_nengo(now.year,now.month)} {now.month}月 {now.day}日" #作成年月日
    year = context['year']
    month = context['month']
    ws['AX7'] = f"{to_nengo(year,month)} {month}月 1日" #todo届出年月日

    insured_number = str(user.insured_number) #被保険者番号
    print(insured_number,flush=True)
    for i,d in enumerate(insured_number):
        cell = f"{chr(ord('G')+i)}7"
        ws[cell] = d
    ws['V7'] = user.name_kana
    ws['V8'] = user.name
    birth = user.date_of_birth
    year = birth.year
    month = birth.month
    day = birth.day
    ws['G9'] = to_nengo(year,month) #年号を表示
    ws['G11'] = f"{month}月{day}日" #年号以下表示
    ws['N9'] = user.get_gender_display()[:1] #性別一字

    ws['W9'] = user.care_level
    ws['W11'] = '' #変更後
    ws['W12'] = '' #変更日
    ws['AI9'] = user.max_separate_payment #限度額
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
        ws[f'H{row}'] = f'{plan.service_name}'
        ws[f'O{row}'] = office_name[0]
        ws[f'O{row+1}'] = office_name[1]
        for i,c in enumerate(calendar):
            col = get_column_letter(25 + i)
            day = str(c['day'])
            ws[f'{col}{row}'] = plan.schedule_dict.get(day,'')
            ws[f'{col}{row+1}'] = plan.actual_dict.get(day,{}).get('main','')
        row += 2



    ws = wb['2'] #別シート
    ws['AW1'] = f"{to_nengo(now.year,now.month)} {now.month}月 {now.day}日"
    ws['AW2'] = user.name
    ws['AH2'] = insured_number
    ws.title = '別表（実績）'
    wb.save(f'サービス提供表_{user.name}_{year}_{month}.xlsx')
    return wb
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