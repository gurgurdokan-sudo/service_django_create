import os
import boto3

from urllib.parse import quote
from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from dashboard.models import User
from dashboard.excel.excel_writer import get_service_sheet_path, create_service_sheet
from dashboard.views.user_service_view import build_user_service_context

import logging
logger = logging.getLogger(__name__)

def download_service_sheet(request, user_id):
    """
        Excelファイルをダウンロードするビュー関数。ユーザーIDと年月を指定して、既に作成済みのサービス提供表を返す。
        ローカル環境ではファイルシステムから、S3環境ではS3バケットからファイルを取得する。
    """    
    user = get_object_or_404(User, id=user_id)
    year = int(request.GET.get('dis_year',2000))
    month = int(request.GET.get('dis_month',1))
# ローカルの場合
    if settings.DJANGO_ENV == 'dev':
        file_path, filename = get_service_sheet_path(user, year, month)
        if not (file_path or os.path.exists(file_path)):
            messages.error(request, 'ファイルが作成されていません')
            return redirect('dashboard:user_list')
        with open(file_path, 'rb') as f:
            response = HttpResponse(
                f.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            logger.info(f'{filename}を出力')
            response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
            return response

# s3の場合
    else:
        key, filename = get_service_sheet_path(user, year, month)
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
        file_bytes = obj['Body'].read()
        response = HttpResponse(
            file_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response

def export_excel(request,user_id):
    now = timezone.now()
    year = int(request.GET.get('dis_year', now.year))
    month = int(request.GET.get('dis_month', now.month))
    logger.info(f'{year}-{month}をExcel出力')
    context = build_user_service_context(user_id=user_id,year=year,month=month)
    # if context['plan'] is None:
    #     messages.error(request,'プランが作成されていません')
    #     return redirect('dashboard:user_list')
    # if context['user'].care_level == '認定情報更新が必要':
    #     messages.error(request,'認定情報が更新されていません')
    #     return redirect('dashboard:user_list')
    # if context['user'].care_manager is None:
    #     messages.error(request,'ケアマネジャーが設定されていません')
    #     return redirect('dashboard:user_list')
    # if context['office'] is None:
    #     messages.error(request,'事業所が設定されていません')
    #     return redirect('dashboard:user_list')
    
    create_service_sheet(context)
    messages.success(request,'Excelを作成しました')
    return redirect('dashboard:user_list')