# export_service_sheet.py
"""サービス提供表（Excel）の作成：各Sheetの書き込みを呼び出し、保存と月次実績の更新を行う。"""
import os
import io
from datetime import date
from django.utils.timezone import localdate, now
from django.conf import settings
import boto3
from openpyxl import load_workbook
from dashboard.models import ServiceMonthlyRecord
from dashboard.excel.service_calculator import ServiceSheetCalculator
from dashboard.excel.schedule_sheet import write_schedule_sheet
from dashboard.excel.billing_sheet import write_billing_sheet

import logging
logger = logging.getLogger(__name__)

TEMPLATE_PATH = 'templatesExcel/service_template.xlsx'


def create_service_sheet(context):
    """ビューから呼ばれる入口。計算結果をSheet1・Sheet2に書き、保存して月次実績を更新する。"""
    try:
        wb = load_workbook(TEMPLATE_PATH)
        calc = ServiceSheetCalculator(context)
        res = calc.get_results()

        user = context['user']
        office = context['office']
        year, month = context['dis_year'], context['dis_month']
        created_date = localdate()

        # --- Sheet 1: 基本情報・予定・実績カレンダー ---
        write_schedule_sheet(
            wb['1'], user, office, context['plans'], year, month, created_date
        )

        # --- Sheet 2: 別表（実績） ---
        pub = user.get_public_assistance(year, month)  # 生活保護情報
        write_billing_sheet(wb['2'], calc, res, user, office, created_date, pub)

        _save_workbook(wb, user, year, month)

        # 後処理
        _record_model_update(user, year, month, res)
    except Exception as e:
        logger.error(f"サービス提供表の作成中にエラーが発生しました: {e}")
        raise


def _save_workbook(wb, user, year, month):
    """開発環境ではローカル、それ以外ではS3に保存する。"""
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


def _record_model_update(user, year, month, res):
    """ServiceMonthlyRecordに計算結果を反映する"""
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