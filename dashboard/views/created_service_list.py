from django.shortcuts import render
from dashboard.models import ServiceMonthlyRecord
from django.db.models import Sum

#利用者 作成済み　サービス提供表一覧
def created_service_list(request):
    records = ServiceMonthlyRecord.objects.all().filter(confirmed=True).order_by('-date')
    return render(request, 'dashboard/created_service_list.html', {'records': records})

from django.http import JsonResponse

def created_service_list_api(request):
    year = request.GET.get('year')
    month = request.GET.get('month')

    records = ServiceMonthlyRecord.objects.filter(
        confirmed=True,
        date__year=year,
        date__month=month
    ).order_by('-date')

    # --- 集計 ---
    target_users = records.count()
    confirmed_count = records.filter(confirmed=True).count()
    unconfirmed_count = target_users - confirmed_count

    total_cost = records.aggregate(Sum("total_cost"))["total_cost__sum"] or 0
    benefit_amount = records.aggregate(Sum("benefit_amount"))["benefit_amount__sum"] or 0
    public_amount = records.aggregate(Sum("public_amount"))["public_amount__sum"] or 0
    user_share_amount = records.aggregate(Sum("user_share_amount"))["user_share_amount__sum"] or 0

    # --- 個別レコード ---
    record_list = []
    for r in records:
        record_list.append({
            "user": r.user.name,
            "confirmed": r.confirmed,
            "total_cost": r.total_cost,
            "benefit_amount": r.benefit_amount,
            "public_amount": r.public_amount,
            "user_share_amount": r.user_share_amount,
            "public_flag": r.public_amount > 0
        })

    items = [
                { "label": "請求対象者", "status": "ok", "value": f"{target_users} / {target_users}人" },
                { "label": "サービス提供表", "status": "warning" if unconfirmed_count else "ok",
                  "value": f"{confirmed_count} / {target_users}人 確定" },
                { "label": "介護認定情報", "status": "ok", "value": "OK" },
                { "label": "被保険者番号", "status": "ok", "value": "OK" },
                { "label": "保険者番号", "status": "ok", "value": "OK" },
                { "label": "請求金額計算", "status": "ok", "value": "OK" }
            ]

    return JsonResponse({
        "year": year,
        "month": month,

        "summary": {
            "target_users": target_users,
            "confirmed_count": confirmed_count,
            "unconfirmed_count": unconfirmed_count,
            "total_claim_amount": benefit_amount + public_amount
        },

        "amounts": {
            "total_cost": total_cost,
            "benefit_amount": benefit_amount,
            "public_amount": public_amount,
            "user_share_amount": user_share_amount
        },

        "checks": {
            "total_items": 6,
            "ok_items": len([item for item in items if item["status"] == "ok"]),
            "items": items
        },

        "records": record_list,

        "csv": {
            "status": "not_created",
            "history": []
        }
    })
