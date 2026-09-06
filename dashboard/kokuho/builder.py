from dashboard.models import ServiceMonthlyRecord

class ClaimBuilder:
    def get_target_users(self, year, month):
        return ServiceMonthlyRecord.objects.filter(
            date__year=year,
            date__month=month
        )

    def build_user_claim(self, records, year, month):
        rows = []
        for r in records:
            rows.append({
                "事業所番号": r.office.officenumber,
                "サービス提供年月": f"{year}{month:02d}",
                "保険者番号": r.user.insurer_number,
                "被保険者番号": r.user.insured_number,
                "サービス種類": r.service_type,
                "要介護度": r.user.care_level,
                "サービスコード": r.service_code,
                "サービス提供回数": r.count,
                "単位数": r.units,
                "単位数単価": r.unit_price,
                "請求額": r.benefit_amount + r.public_amount,
                "公費": r.public_amount,
                "本人負担": r.user_share_amount,
            })
        return rows
