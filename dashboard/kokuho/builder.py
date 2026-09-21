from datetime import date

from dateutil.relativedelta import relativedelta
from dashboard.models.const import (
    DATA_TYPE_CARE_INSURANCE,
    CLAIM_CATEGORY,
    CLAIM_DETAIL_CATEGORY,
    DATA_SET_CLAM
)
from dashboard.models import ServiceMonthlyRecord


class ClaimBuilder:

    def __init__(self, office, year, month):
        self.office = office
        self.year = year
        self.month = month

        self.target_year_month = f"{year}{month:02d}" # 出請求書作成年月
        # --------------------------------------------------
        # CSV作成年月
        #
        # 現在は暫定的に「請求対象年月の翌月」
        # 将来的には request 等から指定する
        # create_year = request.GET.get("create_year")
        # create_month = request.GET.get("create_month")
        # --------------------------------------------------
        create_month =''
        create_year = ''
        if create_year is None or create_month is None:
            next_month = date(year, month, 1) + relativedelta(months=1)

            self.create_year = next_month.year
            self.create_month = next_month.month
        else:
            self.create_year = create_year
            self.create_month = create_month
        self.create_year_month =f'{self.create_year}{self.create_month:02d}' #請求対象のサービス提供年月


        self.records = ServiceMonthlyRecord.objects.filter(
                                                    office=office,
                                                    date__year=year,
                                                    date__month=month,
                                                ) #QueySet 

        self.row = 0

    def count_up_row(self): #行番号をカウント
        self.row += 1
        return self.row
    
    def build_office_claim_header(self):
        """
        請求書情報：基本情報レコード(国保連CSV 1行目)
        """
        RECORD_TYPE_HEADER = 1
        record_set = DATA_SET_CLAM.get(self.office.service_type_code)
        if not record_set:
            raise ValueError("対応するレコードセットがありません")
            
        return [
            RECORD_TYPE_HEADER,            #レコード識別子（固定1
            self.count_up_row(),           #連番
            0,                             #交換識別子（通常請求 固定0
            record_set['item_number'],     #項番
            record_set['claim_category'],  #請求分類コード 7110 or 7111
            self.office.pref_code,         #都道府県コード  propertyでスライス
            0,                             #請求区分　通常請求 固定0
            self.office.office_number,     #事務所番号
            0,                             #作成区分　固定0
            DATA_TYPE_CARE_INSURANCE,      #データ種別　7=介護給付請求
            self.target_year_month,        #請求年月
            0,                             #予備/送信回数 固定0
        ]
    def build_office_claim_details(self, records):
        """
        請求書情報：明細情報レコード（国保連CSV 2~N行目）
        """
        RECORD_TYPE_DETAIL = 2
        
        claim_details = []

        # サービス種類単位で集計
        service_groups = {}

        for record in records:
            for plan in record.plans.all():
                key = plan.service_code

                if key not in service_groups:
                    service_groups[key] = {
                        "count": 0,
                        "units": 0,
                    }

                # 実績回数と単位数の集計
                service_groups[key]["count"] += plan.get_total_count("actual")
                service_groups[key]["units"] += plan.total_actual_units

        # 明細内の行番号カウンター（1, 2, 3...）
        detail_line_number = 0

        for service_code, data in service_groups.items():
            detail_line_number += 1

            # 総単位数（保険給付対象）
            total_units = data["units"]

            claim_details.append([
                RECORD_TYPE_DETAIL,             #  レコード識別子 (固定: 2)
                self.count_up_row(),            #  全体連番 (行番号)
                7111,                           #  サービス費用コード (7111)
                self.target_year_month,         #  請求年月 (YYYYMM)
                self.office.office_number,      #  事業所番号
                
                detail_line_number,             #  明細行番号 (1, 2, 3...)
                self.office.service_type_code,  #  サービス種類コード (例: 15 または 78)
                "01",                           #  サービス区分コード (固定: "01")
                
                data["count"],                  #  延べ件数/回数
                service_code,                   #  サービスコード (6桁)
                total_units,                    #  請求単位数
                
                total_units,                    #  保険給付対象単位数
                0,                              #  超過・自費単位数
                0,                              #  公費対象単位数
                0,                              #  保険給付請求額
                0,                              #  公費請求額
                0,                              #  利用者負担額
                0,                              #  予備
                0,                              #  予備
                0,                              #  予備
            ])

        return claim_details
    
    def build_user_claim(self):
        """
        利用者ごとの請求情報を作る。

        ここでは ServiceMonthlyRecord と ServicePlan から
        必要な情報を取り出す。

        最終的には国保連の利用者単位のレコードへ
        変換する。
        """

        rows = []

        for record in self.records:
            for plan in record.plans.all():

                rows.append({
                    "office_number": self.office.office_number,
                    # 請求対象年月
                    "service_month": self.service_year_month,
                    # 利用者
                    "insured_number": record.user.insured_number,
                    # 認定
                    "care_level": plan.care_level,
                    # サービス
                    "service_code": plan.service_code,
                    # 実績
                    "count": plan.get_total_count("actual"),
                    # 単位数
                    "units": plan.total_actual_units,
                })

        return rows


    def build(self):
        """
        国保請求CSVを構成する全レコードを作る。

        現時点では

            1. 請求書基本情報
            2. 請求書明細情報
            3. 利用者ごとの請求情報

        の順に構築する。
        """

        rows = []

        # 1. 請求書基本情報
        rows.append(
            self.build_office_claim_header()
        )

        # 2. 請求書明細情報
        rows.extend(
            self.build_office_claim_details()
        )

        # 3. 利用者ごとの請求情報
        rows.extend(
            self.build_user_claim()
        )

        return rows