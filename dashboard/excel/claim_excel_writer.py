import os

from django.conf import settings
from openpyxl import load_workbook
from dashboard.models import ServiceMonthlyRecord
from dashboard.excel.service_calculator import ServiceSheetCalculator
from dashboard.excel.schedule_sheet import write_schedule_sheet
from dashboard.excel.billing_sheet import write_billing_sheet

import logging
logger = logging.getLogger(__name__)
TEMPLATE_PATH = 'templatesExcel/claim_template.xlsx'

def create_claim_invoice_excel(context):
    return
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
