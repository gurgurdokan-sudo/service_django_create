from datetime import date

from django.shortcuts import render
from django.db.models import Sum
from django.http import JsonResponse

from dashboard.models import ServiceMonthlyRecord, OfficeMonthlyBilling, Office
from dashboard.utils import BreadcrumbUtil  
import logging
logger = logging.getLogger(__name__)

#利用者 作成済み　サービス提供表一覧
def created_service_list(request):
    crumbs = [
        # ("利用者一覧", "dashboard:user_list"),
        ("サービス提供 作成状況",None)
    ]
    records = ServiceMonthlyRecord.objects.all().filter(confirmed=True).order_by('-date')
    return render(
        request, 
        'dashboard/created_service_list.html', {
        'records': records,
        'breadcrumbs': BreadcrumbUtil.create(crumbs)
        })



def created_service_list_api(request):
    year = int(request.GET.get("year"))
    month = int(request.GET.get("month"))

    # todo 事業所（Office）の取得方法（ログインユーザーに紐づく事業所）
    # office = request.user.office
    office = Office.objects.get(id=1)  # 事業所ID  

    billing_date = date(year, month, 1)

    # --- レコード取得 ---
    month_records = ServiceMonthlyRecord.objects.filter(
        office=office, # 事業所での絞り込み
        # user__is_active=True, # 有効な利用者のみ
        date__year=year,
        date__month=month,
    ).order_by("-date")
    
    # --- 確定済みレコードの抽出 ---
    confirmed_records = month_records.filter(confirmed=True)

    # --- 人数集計 ---
    target_users = month_records.count()
    confirmed_count = confirmed_records.count()
    unconfirmed_count = target_users - confirmed_count

    # --- 金額集計 ---
    total_cost = (
        confirmed_records.aggregate(Sum("total_cost"))["total_cost__sum"] or 0
    )
    benefit_amount = (
        confirmed_records.aggregate(Sum("benefit_amount"))[
            "benefit_amount__sum"
        ]
        or 0
    )
    public_amount = (
        confirmed_records.aggregate(Sum("public_amount"))["public_amount__sum"]
        or 0
    )
    user_share_amount = (
        confirmed_records.aggregate(Sum("user_share_amount"))[
            "user_share_amount__sum"
        ]
        or 0
    )
    total_claim_amount = benefit_amount + public_amount

    # --- OfficeMonthlyBilling への保存/更新 ---
    billing, _ = OfficeMonthlyBilling.objects.update_or_create(
        office=office,
        billing_month=billing_date,
        defaults={
            "total_amount": total_claim_amount,
        },
    )

    # --- 個別レコード構築 ---
    record_list = []
    for r in month_records:
        record_list.append(
            {
                "user": r.user.name,
                "confirmed": r.confirmed,
                "total_cost": r.total_cost,
                "benefit_amount": r.benefit_amount,
                "public_amount": r.public_amount,
                "user_share_amount": r.user_share_amount,
                "public_flag": r.public_amount > 0,
            }
        )

    # --- チェック項目 ---
    users:list = [r.user for r in month_records]
    check_certificate:dict = _check_certificate(users, year, month)
    check_insured_numbers:dict = _check_insured_numbers(users)
    check_public_assistance:dict = _check_public_assistance(month_records, year, month)
    check_cara_management:dict = _check_cara_management(users)
    items =[
        {
            "label": "サービス提供票の確定",
            "status": "warning" if unconfirmed_count else "ok",
            "value": f"{confirmed_count} / {target_users}人 確定済み",
        },
        check_insured_numbers,
        check_public_assistance,
        check_certificate,
        check_cara_management,
    ]
    
    # --- CSV情報の組み立て ---
    csv_status = "created" if billing.is_csv_issued else "not_created"
    csv_history = []
    if billing.is_csv_issued:
        csv_history.append(
            {
                "generated_at": (
                    billing.csv_generated_at.strftime("%Y-%m-%d %H:%M")
                    if billing.csv_generated_at
                    else ""
                ),
                "file_url": (
                    billing.kokuhoren_csv.url if billing.kokuhoren_csv else ""
                ),
            }
        )

    return JsonResponse(
        {
            "year": str(year),
            "month": str(month),
            "summary": {
                "target_users": target_users,
                "confirmed_count": confirmed_count,
                "unconfirmed_count": unconfirmed_count,
                "total_claim_amount": total_claim_amount,
            },
            "amounts": {
                "total_cost": total_cost,
                "benefit_amount": benefit_amount,
                "public_amount": public_amount,
                "user_share_amount": user_share_amount,
            },
            "checks": {
                "total_items": len(items),
                "ok_items": sum(item["status"] == "ok" for item in items),
                "items": items,
            },
            "records": record_list,
            "csv": {
                "status": csv_status,
                "is_issued": billing.is_csv_issued,
                "generated_at": (
                    billing.csv_generated_at.isoformat()
                    if billing.csv_generated_at
                    else None
                ),
                "file_url": (
                    billing.kokuhoren_csv.url if billing.kokuhoren_csv else None
                ),
                "history": csv_history,
            },
        }
    )
def _check_certificate(users, year, month) -> dict:
    if not users:
        return {
            "label": "介護認定情報",
            "status": "warning",
            "value": "対象者なし",
        }

    missing = [
        user.name
        for user in users
        if user.get_certificate(year, month) is None
    ]

    return {
        "label": "介護認定情報",
        "status": "error" if missing else "ok",
        "value": (
            f"{len(users) - len(missing)} / {len(users)}人 OK"
            if not missing
            else f"未登録 {len(missing)}人"
        ),
    }
def _check_insured_numbers(users) -> dict:
    for user in users:
        user_insured_number = user.insured_number
        if not user_insured_number or int(user_insured_number) <= 0 or len(user_insured_number) != 10:
            return {
                        "label": "被保険者番号",
                        "status": "error",
                        "value": "登録情報に不正な被保険者番号があります"
                    }
    return {
                "label": "被保険者番号",
                "status": "ok",
                "value": "確認済み"
            }
def _check_public_assistance(records, year, month) -> dict:
    # 公費請求額が発生している記録だけ確認する
    public_records = [
        record for record in records
        if (record.public_amount or 0) > 0
    ]

    missing = [
        record.user.name
        for record in public_records
        if record.user.get_public_assistance(year, month) is None
    ]

    if missing:
        return {
            "label": "公費負担医療費",
            "status": "error",
            "value": f"公費情報が未登録 {len(missing)}人",
        }

    if not public_records:
        return {
            "label": "公費負担医療費",
            "status": "ok",
            "value": "対象者なし",
        }

    return {
        "label": "公費負担医療費",
        "status": "ok",
        "value": f"{len(public_records)}人確認済み",
    }

def _check_cara_management(users) -> dict:
    if not users:
        return {
            "label": "ケアマネジャー",
            "status": "warning",
            "value": "対象者なし",
        }

    missing = [
        user.name
        for user in users
        if getattr(user, "care_manager", None) is None
    ]

    if missing:
        return {
            "label": "ケアマネジャー",
            "status": "error",
            "value": f"未登録 {len(missing)}人",
        }

    return {
        "label": "ケアマネジャー",
        "status": "ok",
        "value": f"{len(users)}人確認済み",
    }
    