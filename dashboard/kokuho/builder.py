from dashboard.models import ServiceMonthlyRecord
''''請求情報を取得'''
def get_target_users(year, month):
    return ServiceMonthlyRecord.objects.filter(
        date__year=year,
        date__month=month
    )
class ClaimBuilder:
    """請求情報を構築するクラス"""
    def build_user_claim(self, record):
        return {
            "user": record.user,
            "services": self.build_services(record),
            "basic": self.build_basic_info(record),
            "details": self.build_detail_records(record),
            "summary": self.build_summary(record),
        }
class ClaimDocument:
    """ 請求書のドキュメントを表すクラス """
    def __init__(self, basic, details, summary):
        self.basic = basic
        self.details = details
        self.summary = summary
