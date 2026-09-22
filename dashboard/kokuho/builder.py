from asyncio.windows_events import NULL
from datetime import date

from dateutil.relativedelta import relativedelta

from dashboard.excel.service_calculator import ServiceSheetCalculator
from dashboard.models.const import (
    DATA_TYPE_CARE_INSURANCE,
    DATA_SET_CLAM
)
from dashboard.models import ServiceMonthlyRecord


class ClaimBuilder:
    #定数
    RECORD_TYPE_HEADER = 1          # ヘッダーレコード
    RECORD_TYPE_DETAIL = 2          # 事業所の詳細レコード
    RECORD_TYPE_END = 3             # 全体の最終レコード

    USER_RECORD_BASIC = '01'        # 利用者の認定・基本情報
    USER_RECORD_SERVICE = '02'      # サービス提供情報
    USER_RECORD_TOTAL = '10'        # 集計情報

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

        return [
            self.RECORD_TYPE_HEADER,            # レコード識別子（固定1
            self.count_up_row(),                # 連番
            0,                                  # 交換識別子（通常請求 固定0
            self.record_set['item_number'],     # 項番
            self.record_set['claim_category'],  # 請求分類コード 7110 or 7111
            0, #todo 仕様確認
            # self.office.pref_code,            # 都道府県コード  propertyでスライス
            0,                                  # 請求区分　通常請求 固定0
            self.office.office_number,          # 事務所番号
            0,                                  # 作成区分　固定0
            DATA_TYPE_CARE_INSURANCE,           # データ種別　7=介護給付請求
            self.target_year_month,             # 請求年月
            0,                                  # 予備/送信回数 固定0
        ]
    def build_office_claim_details(self):
        """
        請求書情報：明細情報レコード（国保連CSV 2~N行目）
        """

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
                self.RECORD_TYPE_DETAIL,                 #  レコード識別子 (固定: 2)
                self.count_up_row(),                #  全体連番 (行番号)
                self.record_set['detail_category'], #  サービス費用コード (7111)
                self.target_year_month,             #  請求年月 (YYYYMM)
                self.office.office_number,          #  事業所番号
                
                detail_line_number,                 #  明細行番号 (1, 2, 3...)
                self.office.service_type_code,      #  サービス種類コード (例: 15 または 78)
                self.USER_RECORD_BASIC,             #  サービス区分コード (固定: "01")
                
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

    def build_user_claim_basic(self):
        cert = self.user.get_certificate(
            self.year,
            self.month,
            # is_active=True
        )
        if not cert:
            raise ValueError(
                f"認定情報がありません: "
                f"insured_number={self.user.insured_number}, "
                f"year={self.year}, "
                f"month={self.month}"
            )
        elif not cert.is_active :
            '''一旦例外 その時有効なら使える'''
            raise ValueError(
                f"認定情報が変更されています"
                f"insured_number={self.user.insured_number}, "
                f"year={self.year}, "
                f"month={self.month}"
            )

        return [
            self.RECORD_TYPE_DETAIL,
            self.count_up_row(),                            # 全体連番
            self.record_set["claim_home_based_category"],   # サービス費用コード
            self.USER_RECORD_BASIC,                         # 利用者基本・認定レコード
            self.target_year_month,                         # 請求年月
            self.office.office_number,                      # 事業所番号
            self.office.municipality.municipality_code,     # 市町村コード
            self.user.insured_number,                            # 被保険者番号
            self.user.birth_date_value,                          # 生年月日(YYYYMM)
            self.user.gender_disp,                               # 性別区分(男1
            cert.convert_care_level,                        # 介護度を国保連用コードに変換
            cert.certification_start,                       # 適用開始日(YYYYMM)
            cert.certification_end,                         # 適用終了日(YYYYMM)

            # 以降よくわからない
            1,
            self.user.care_manager.care_management_office_number,# 居宅介護支援事業所番号
            None,
            None,
            None,
            None,
            None,
            0,
            0,
            None,
            cert,
            0,
            0,
            0,
            8608,
            self.record.user_share_amount,                  # 利用者負担額
            8996,

            # 予備
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

    def build_user_claim_details(self):
        """
        利用者1人分の 02 レコードを作る。
        """
        rows = []
        for plan in self.plans:
            count = int(plan.get_total_count("actual"))
            unit = int(plan.unit)
            subtotal = (unit * count)
            rows.append([ #プランごとの行
                self.RECORD_TYPE_DETAIL,
                self.count_up_row(),
                self.record_set["claim_home_based_category"],           # サービス費用コード
                self.USER_RECORD_SERVICE,
                self.target_year_month,                                 # 請求年月
                self.office.office_number,                              # 事業所番号
                self.office.municipality.municipality_code,             # 市町村コード
                self.user.insured_number,                                    # 被保険者番号
                self.office.service_type_code,                          # サービス種類
                str(plan.service_code),                                 # サービスコード
                unit,                                                   # 単価
                count,                                                  # 回数
                # 予備
                0,
                0,
                0,
                subtotal,                                                # 小計単位数
                0,
                0,
                0,
                "",
            ])
        return rows
    def build_user_claim_total(self):
        """
            利用者1人分の 02 レコードを作る。
        """
        add_codes = {}

        context = {
            "office": self.office,
            "user": self.user,
            "plans": self.plans,
            "add_codes": add_codes, #todo 空の加算
            "dis_year": self.year,
            "dis_month": self.month,
        }

        calculator = ServiceSheetCalculator(context)
        result = calculator.get_results()

        actual_count = sum(
            int(
                plan.get_total_count("actual")
            )
            for plan in self.plans
        )

        service_units = sum(
            int(plan.total_actual_units)
            for plan in self.plans
        )
        total_units = int(
            result["subtotal_units"]
        )

        addon_units = max(
            0,
            total_units - service_units
        )
        claim_units = (
            service_units + addon_units
        )
        return [
            self.RECORD_TYPE_DETAIL,
            self.count_up_row(),                                # 全体連番
            self.record_set["claim_home_based_category"],       # サービス費用コード
            self.USER_RECORD_TOTAL,
            self.target_year_month,                             # 請求年月
            self.office.office_number,                          # 事業所番号
            self.office.municipality.municipality_code,         # 市町村コード
            self.user.insured_number,                           # 被保険者番号
            self.office.service_type_code,                      # サービス種類
            actual_count,                                       # 給付日数 / 利用日数
            service_units,                                      # 計画単位数
            service_units,                                      # 実績単位数
            addon_units,                                        # 加算単位数

            # 以下はCSV仕様上の金額項目
            0,
            0,
            0,
            claim_units,                                        # 総請求単位数
            result["insurance_seikyu"],                         # 保険請求
            result["public_seikyu"],                            # 公費請求
            result["user_hutan"],                               # 本人支払(超過分込)

            # 予備
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ]
    def build_user_claim(self, record):
        self.record = record
        self.plans = list(self.record.plans.all())
        self.user = self.record.user
        if not self.user.care_manager:
            raise ValueError(f'ケアマネジャーが設定されていない利用者={self.user.name}')
        # 01
        rows = [self.build_user_claim_basic()]

        # 02
        rows.extend(
            self.build_user_claim_details()
        )

        # 10
        rows.append(
            self.build_user_claim_total()
        )

        return rows

    def build_office_claim_end(self):
        return [
            self.RECORD_TYPE_END,
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
        # 1. 請求書基本情報
        rows = [self.build_office_claim_header()]

        # 2. 請求書明細情報
        rows.extend(
            self.build_office_claim_details()
        )

        # 3. 利用者ごとの請求情報を作成し、仕様順に直す 1~3行
        for record in self.records:
            rows.extend(
                self.build_user_claim(record)
            )
        # 5. エンドの行
        rows.append(
            self.build_office_claim_end()
        )
        return rows