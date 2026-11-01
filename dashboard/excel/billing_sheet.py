# billing_sheet.py
"""Sheet2（別表（実績））：Plan・加算の明細、集計行、合計欄を書く。"""
from openpyxl.styles import Alignment

from dashboard.excel.service_calculator import format_comma
from dashboard.excel.excel_utils import auto_newline

SHEET_TITLE = '別表（実績）'
FIRST_DETAIL_ROW = 6  # 明細の1行目
TOTAL_ROW = 20  # 最終合計行（テンプレートで固定）
BIKOU_START_ROW = 23  # 備考欄（AK列）の1行目
SERVICE_TYPE_TOTAL_NAME = '地域密着通所合計'


def write_billing_sheet(ws, calc, res, user, office, created_date, pub):
    """Sheet2に明細・サービス種類集計・デフォルト加算・合計・備考を書く。"""
    ws.title = SHEET_TITLE
    ws['AW1'] = f"{created_date.year}年{created_date.month}月{created_date.day}日"
    ws['AH2'] = user.insured_number
    ws['AW2'] = user.name
    office.simple_name = office.name.split()[:2]

    # Sheet2はPlan・加算の明細を出し、全体集計とデフォルト加算を続ける。
    current_row = FIRST_DETAIL_ROW
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
        write_billing_line(ws, current_row, item, office)
        current_row += 1

    # Plan・加算の集計は1行だけ出し、単位数を括弧で囲む。
    if detail_rows:
        summary_item = _build_summary_item(detail_rows, calc, res)
        write_service_type_total(ws, current_row, summary_item, office)
        current_row += 1

    # 集計行の直下にデフォルト加算（処遇改善加算）を出す。
    default_item = _build_default_item(office, calc, res)
    if default_item is not None:
        write_billing_line(ws, current_row, default_item, office)
        current_row += 1

    # 20行目は最終合計欄のため、明細・集計行がここまで達したらエラーにする。
    if current_row >= TOTAL_ROW:
        raise ValueError("Sheet2の明細・集計行が固定合計欄（20行目）に重なります")

    _write_total_row(ws, res)
    _write_bikou(ws, pub)


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
    auto_newline(item['name'], ws, f'L{row}', 6)
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


def _build_summary_item(detail_rows, calc, res):
    """明細を合算し、サービス種類の集計行（地域密着通所合計）を作る。"""
    return {
        'name': SERVICE_TYPE_TOTAL_NAME,
        'subtotal': _sum_int(detail_rows, 'subtotal'),
        'cost_total': _sum_int(detail_rows, 'cost_total'),
        'benefit_rate': calc.benefit_rate,
        'benefit_amount': _sum_int(detail_rows, 'benefit_amount'),
        'public_amount': _sum_int(detail_rows, 'public_amount'),
        'user_share_amount': _sum_int(detail_rows, 'user_share_amount'),
        'parenthesize_subtotal': True,
        'within_units': res['within_units'],
    }


def _build_default_item(office, calc, res):
    """デフォルト加算（処遇改善加算）の行を作る。出力しない場合はNoneを返す。"""
    default_service = office.default_service
    default_units = int(res.get('def_unit') or 0)
    if not default_service or default_units <= 0:
        return None

    default_cost = int(res.get('def_total_cost') or 0)
    default_benefit = int(default_cost * calc.benefit_rate)
    default_share =  default_cost - default_benefit
    return {
        'name': default_service.service_name,
        'code': f"{office.service_type_code}{default_service.code}",
        'unit': '',
        'count': '',
        'subtotal': default_units,
        'cost_total': default_cost,
        'benefit_rate': calc.benefit_rate,
        'benefit_amount': default_benefit,
        'user_share_amount': default_share,
        'parenthesize_subtotal': True,
        'is_subtotal': True,
        'is_default': True,
        'within_units': res['within_units'],
    }


def _write_total_row(ws, res):
    """最終合計行（20行目固定）を書く。"""
    # 費用総額・保険給付額・利用者負担は各明細行に出力済み。
    # 明細の直後に合計金額を重ねて書くと二重計上になるため、全体合計は20行目だけに出す。
    ws[f'AT{TOTAL_ROW}'] = format_comma(res['total_cost'])
    ws[f'AX{TOTAL_ROW}'] = format_comma(res['benefit_amount'])
    ws[f'BG{TOTAL_ROW}'] = format_comma(res['user_share_amount'])


def _write_bikou(ws, pub):
    """生活保護の場合、備考欄に法別番号・公費負担者番号・公費受給者番号を書く。"""
    if not pub:
        return
    bikou_text = [
        "生活保護の法別番号:25 ",
        f"公費負担者番号:{pub.hogo_number} ",
        f"公費受給者番号:{pub.recipient_number}",
    ]
    for i, text in enumerate(bikou_text):
        ws[f'AK{BIKOU_START_ROW + i}'] = text


def _sum_int(rows, key):
    """明細の指定キーを整数として合計する。"""
    return sum(int(row.get(key) or 0) for row in rows)