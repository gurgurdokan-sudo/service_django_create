from asyncio.windows_events import NULL
from datetime import date

from dateutil.relativedelta import relativedelta
from dashboard.models.const import (
    DATA_TYPE_CARE_INSURANCE,
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
        create_month =None
        create_year = None
        if create_year is None or create_month is None:
            next_month = date(year, month, 1) + relativedelta(months=1)

            self.create_year = next_month.year
            self.create_month = next_month.month
        else:
            self.create_year = create_year
            self.create_month = create_month
        #
        self.record_set = DATA_SET_CLAM.get(self.office.service_type_code)
        if not self.record_set:
            raise ValueError("対応するレコードセットがありません")

        self.create_year_month =f'{self.create_year}{self.create_month:02d}' #請求対象のサービス提供年月


        self.records = (
            ServiceMonthlyRecord.objects.filter(
                                                    office=office,
                                                    date__year=year,
                                                    date__month=month,
                                                )) #QueySet

        self.row = 0

    def count_up_row(self): #行番号をカウント
        self.row += 1
        return self.row
    
    def build_office_claim_header(self):
        """
        請求書情報：基本情報レコード(国保連CSV 1行目)
        """
        RECORD_TYPE_HEADER = 1

        return [
            RECORD_TYPE_HEADER,                 #レコード識別子（固定1
            self.count_up_row(),                #連番
            0,                                  #交換識別子（通常請求 固定0
            self.record_set['item_number'],     #項番
            self.record_set['claim_category'],  #請求分類コード 7110 or 7111
            self.office.pref_code,              #都道府県コード  propertyでスライス
            0,                                  #請求区分　通常請求 固定0
            self.office.office_number,          #事務所番号
            0,                                  #作成区分　固定0
            DATA_TYPE_CARE_INSURANCE,           #データ種別　7=介護給付請求
            self.target_year_month,             #請求年月
            0,                                  #予備/送信回数 固定0
        ]
    def build_office_claim_details(self):
        """
        請求書情報：明細情報レコード（国保連CSV 2~N行目）
        """
        RECORD_TYPE_DETAIL = 2
        
        claim_details = []

        # サービス種類単位で集計
        service_groups = {}

        for record in self.records:
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
                RECORD_TYPE_DETAIL,                 #  レコード識別子 (固定: 2)
                self.count_up_row(),                #  全体連番 (行番号)
                self.record_set['detail_category'], #  サービス費用コード (7111)
                self.target_year_month,             #  請求年月 (YYYYMM)
                self.office.office_number,          #  事業所番号
                
                detail_line_number,                 #  明細行番号 (1, 2, 3...)
                self.office.service_type_code,      #  サービス種類コード (例: 15 または 78)
                self.record_set['classification_code'],#  サービス区分コード (固定: "01")
                
                data["count"],                      #  延べ件数/回数
                service_code,                       #  サービスコード (6桁)
                total_units,                        #  請求単位数
                
                total_units,                        #  保険給付対象単位数
                0,                                  #  超過・自費単位数
                0,                                  #  公費対象単位数
                0,                                  #  保険給付請求額
                0,                                  #  公費請求額
                0,                                  #  利用者負担額
                0,                                  #  予備
                0,                                  #  予備
                0,                                  #  予備
            ])

        return claim_details

    def build_user_claim_basic(self, record):
        RECORD_TYPE_DETAIL = 2
        USER_RECORD_BASIC = '01'
        user = record.user
        care_level_code = record.care_level_code
        cert = user.get_certificate(
            self.year,
            self.month,
            # is_active=True
        )
        if not cert:
            raise ValueError(
                f"認定情報がありません: "
                f"insured_number={user.insured_number}, "
                f"year={self.year}, "
                f"month={self.month}"
            )
        elif cert.is_active :
            '''一旦例外 その時有効なら使える'''
            raise ValueError(
                f"認定情報が変更されています"
                f"insured_number={user.insured_number}, "
                f"year={self.year}, "
                f"month={self.month}"
            )

        return [
            RECORD_TYPE_DETAIL,
            self.count_up_row(),                            # 全体連番
            self.record_set["claim_home_based_category"],   # サービス費用コード
            USER_RECORD_BASIC,                              # 利用者基本・認定レコード
            self.target_year_month,                         # 請求年月
            self.office.office_number,                      # 事業所番号
            self.office.municipality.municipality_code,     # 市町村コード
            user.insured_number,                            # 被保険者番号
            user.birth_date_value,                          # 生年月日19341126
            user.gender_disp,                               # 性別区分(男1
            cert.convert_care_level,                        # 介護度を国保連用コードに変換
            cert.certification_start,                       # 適用開始日20251208
            cert.certification_end,                         # 適用終了日20261231

            # 以降よくわからない
            1,
            user.care_manager.care_management_office_number,# 居宅介護支援事業所番号
            None,
            None,
            None,
            None,
            None,
            0,
            0,
            None,
            90,
            0,
            0,
            0,
            8608,
            record.user_share_amount,                       # 利用者負担額
            8996,
            None,
            None,
            None,
            0,
            0,
            0,
            None,
            None,
            None,
            0,
            0,
            0,
            None,
            None,
            None,
            0,
            0,
        ]

    def build_user_claim_details(self, record):
        """
        利用者1人分の 02 レコードを作る。
        """
        RECORD_TYPE_DETAIL = 2
        RECORD_TYPE_USER_TOTAL = 2
        USER_RECORD_SERVICE = '02'
        rows = []
        user = record.user

        plans = list(record.plans.all())
        for plan in plans:
            count = int(plan.get_total_count("actual"))
            unit = int(plan.unit)
            subtotal = (unit * count)
            rows.append([
                RECORD_TYPE_DETAIL,
                self.count_up_row(),
                self.record_set["claim_home_based_category"],           # サービス費用コード
                USER_RECORD_SERVICE,
                self.target_year_month,                                 # 請求年月
                self.office.office_number,                              # 事業所番号
                self.office.municipality.municipality_code,             # 市町村コード
                user.insured_number,                                    # 被保険者番号
                self.office.service_type_code,                          # サービス種類
                str(plan.service_code),                                 # サービスコード
                unit,                                                   # 単価
                count,                                                  # 回数
                0,
                0,
                0,

                # 小計単位数
                subtotal,

                0,
                0,
                0,

                "",
            ])
        return rows

    def build_user_claim(self, record):
        RECORD_TYPE_DETAIL = 2
        RECORD_TYPE_USER_TOTAL = 2
        rows = []
        # 01
        rows.append(
            self.build_user_claim_basic(record)
        )

        # 02
        rows.extend(
            self.build_user_claim_details(record)
        )

        # 10
        rows.append(
            self.build_user_claim_total(record)
        )

        return rows
        users = {}

        for record in user_rows:
            insured_number = record["insured_number"]

            if insured_number not in users:
                users[insured_number] = []

            users[insured_number].append(record)

        rows = []

        for insured_number, records in users.items():

            # -----------------------------
            # 利用者のサービス明細
            # -----------------------------
            for record in records:
                rows.append([
                    RECORD_TYPE_DETAIL,
                    self.count_up_row(),
                    self.record_set['claim_home_based_category'],
                    "02",
                    record["service_month"],
                    record["office_number"],
                    # ここは事業所に紐づく市町村コード
                    self.office.municipality.municipality_code,
                    record["insured_number"],
                    self.office.service_type_code,
                    record["service_code"],
                    # 単価
                    # 現在の中間データには単価がないため要追加
                    0,
                    record["count"],
                    0,
                    0,
                    0,
                    record["units"],
                    0,
                    0,
                    0,
                    "",
                ])

            # -----------------------------
            # 利用者集計
            # -----------------------------
            total_count = sum(
                record["count"]
                for record in records
            )

            total_units = sum(
                record["units"]
                for record in records
            )

            rows.append([
                RECORD_TYPE_USER_TOTAL,
                self.count_up_row(),
                7131,
                "10",
                records[0]["service_month"],
                records[0]["office_number"],
                self.office.municipality.municipality_code,
                insured_number,
                self.office.service_type_code,
                total_count,
                total_units,
                total_units,
                0,
                0,
                0,
                total_units,
                0,
                0,
                0,
            ])

        return rows

    def build_office_claim_end(self,user_row):
        RECORD_TYPE_END = 3
        return [
            RECORD_TYPE_END,
            self.count_up_row(),
        ]

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

        # 3. 利用者ごとの請求情報を作成し、仕様順に直す 1~3行
        rows.extend(
            self.replase_user_claim()
        )
        # 5. エンドの行
        rows.append(
            self.build_office_claim_end()
        )
        return rows