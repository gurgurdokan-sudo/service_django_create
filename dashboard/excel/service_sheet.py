from openpyxl import load_workbook

def create_service_sheet(user, year, month):
    wb = load_workbook('templatesExcel/service_template.xlsx')
    ws = wb.active
    siyaku_number = '112300' #一旦新座市固定
    for i,d in enumerate(siyaku_number):
        cell = f'{chr(ord('K')+i)}5'
        ws[cell] = d
    ws['V5'] = '新座市' #一旦新座市固定
    ws['Aj5'] = '' #介護事業所
    ws['Aj6'] = '' #介護事業担当者
    ws['AX7'] = f"{to_nengo(year)}年{month}月"

    insured_number = str(user.insured_number) #被保険者番号
    for i,d in enumerate(insured_number):
        cell = f"{chr(ord('G')+i)}7"
        ws[cell] = d
    ws['V7'] = user.name_kana
    ws['V8'] = user.name
    ws['W9'] = user.care_level
    ws['W11'] = '' #変更後
    ws['W12'] = '' 
    ws['AI9'] = user.max_separate_payment
    wb.save(f'サービス提供表_{user.name}_{year}_{month}.xlsx')
    return wb
def to_nengo(year, month=1, day=1):
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