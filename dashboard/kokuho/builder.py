from datetime import date
from dateutil.relativedelta import relativedelta
from dashboard.models import ServiceMonthlyRecord
from dashboard.models.const import (
    DATA_TYPE_CARE_INSURANCE,
    DATA_SET_CLAM
)

import logging
logger = logging.getLogger(__name__)

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
        self.municipality_code_zfill=f'{str(self.office.municipality.municipality_code).zfill(8)}'
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
        logger.info('請求書情報：基本情報レコードの作成開始')
        return [
            self.RECORD_TYPE_HEADER,                                # レコード識別子（固定1
            self.count_up_row(),                                    # 全体連番
            0,                                                      # 交換識別子（通常請求 固定0
            self.record_set['item_number'],                         # 項番
            self.record_set['claim_category'],                      # 請求分類コード 7110 or 7111
            0,                                                      # 事務所からの送信の場合は0 固定
            # self.office.pref_code,                                # ↑都道府県コード  propertyでスライス
            0,                                                      # 請求区分　通常請求 固定0
            self.office.office_number,                              # 事務所番号
            0,                                                      # 作成区分　固定0
            DATA_TYPE_CARE_INSURANCE,                               # データ種別　7=介護給付請求
            self.target_year_month,                                 # 請求年月(YYYYMM)
            0,                                                      # 予備/送信回数 固定0
        ]
    def build_office_claim_details(self):
        """
        請求書情報：明細情報レコード（国保連CSV 2~N行目）
        """
        logger.info('請求書情報：明細情報レコードの作成開始')
        claim_details = []

        service_groups = {
            "total_cost": 0,
            "count": 0,
            "units": 0,
            "benefit_amount": 0,
            "public_amount": 0,
            "user_share_amount": 0,
        }
        public_records =[]
        for record in self.records:
            if record.user.get_public_assistance(self.year, self.month) is not None:
                public_records.append(record)
            service_groups["total_cost"] += record.total_cost
            service_groups["count"] += 1
            service_groups["units"] += record.total_units
            service_groups["benefit_amount"] += record.benefit_amount
            service_groups["public_amount"] += record.public_amount or 0
            service_groups["user_share_amount"] += record.user_share_amount or 0
        claim_details.append([
            self.RECORD_TYPE_DETAIL,                            # レコード識別子 (固定: 2)
            self.count_up_row(),                                # 全体連番 (行番号)
            self.record_set['detail_category'],                 # サービス費用コード (7111)
            self.target_year_month,                             # 請求年月 (YYYYMM)
            self.office.office_number,                          # 事業所番号

            1,                                                  # 保険・公費等区分(固定:1)
            0,                                                  # 法別番号 (固定:0)
            self.USER_RECORD_BASIC,                             # サービス区分コード (固定: "01")

            service_groups["count"],                            # 延べ件数
            service_groups["units"],                            # 総単位数
            service_groups["total_cost"],                       # 請求額

            service_groups["benefit_amount"],                   # 保険給付対象請求額
            service_groups["public_amount"],                    # 公費対象請求額
            service_groups["user_share_amount"],                # 利用者負担額
            0, 0, 0, 0, 0, 0,                                   # 予備
        ])

        if len(public_records) == 0:
            logger.info('生活保護対象0件')
            return claim_details

        public_count = len(public_records)
        logger.info(f'生活保護対象{public_count}件')
        public_units = sum(r.total_units for r in public_records)
        public_total_cost = sum(r.total_units for r in public_records)
        public_benefit_amount = 0
        public_share_amount = 0
        claim_details.append([
            self.RECORD_TYPE_DETAIL,                            # レコード識別子 (固定: 2)
            self.count_up_row(),                                # 全体連番 (行番号)
            self.record_set['detail_category'],                 # サービス費用コード (7111)
            self.target_year_month,                             # 請求年月 (YYYYMM)
            self.office.office_number,                          # 事業所番号

            2,                                                  # 保険・公費等区分(固定:2)
            12,                                                 # 生活保護サービス (固定: 12)
            self.USER_RECORD_BASIC,                             # サービス区分コード (固定: "01")

            public_count,                                       # 対象件数
            public_units,                                       # 対象総単位数
            public_total_cost,                                  # 請求額

            public_benefit_amount,                              # 保険給付対象請求額
            service_groups["public_amount"],                    # 公費対象請求額
            public_share_amount,                                # 利用者負担額
            0, 0, 0, 0, 0, 0,                                   # 予備
        ])

        return claim_details

    def _build_user_claim_basic(self):
        """
        利用者1人分の 01 レコードを作る。
            - cert 認定情報を取得
            - 月で認定情報が変更されてる場合を考慮する
        """
        cert = self.user.get_certificate(self.year, self.month)

        if not cert:
            logger.error(f'認定情報がありません: insured_number={self.user.insured_number}, year={self.year}, month={self.month}')
            raise ValueError(
                f"認定情報がありません: "
                f"insured_number={self.user.insured_number}, "
                f"year={self.year}, "
                f"month={self.month}"
            )
        elif not cert.is_active :
            logger.warning(f'認定情報が無効です: insured_number={self.user.insured_number}, year={self.year}, month={self.month}')

        if self.user.get_public_assistance(self.year, self.month): #生活保護があるか
            logger.info(f'生活保護対象者です: insured_number={self.user.insured_number} user={self.user.name}')
            public_assist_units = self.record.total_units
            public_amount = self.record.public_amount
            hogo_number = self.user.get_public_assistance(self.year, self.month).hogo_number
            recipient_number = self.user.get_public_assistance(self.year, self.month).recipient_number
            public_rate = 100
        else:
            public_assist_units = 0
            public_amount = 0
            hogo_number = ""
            recipient_number = ""
            public_rate = 0
        return [
            self.RECORD_TYPE_DETAIL,                                    # レコード識別子（固定: 2）
            self.count_up_row(),                                        # 全体連番
            self.record_set["claim_home_based_category"],               # サービス費用コード(固定:7131)
            self.USER_RECORD_BASIC,                                     # 利用者基本・認定レコード(固定:01)
            self.target_year_month,                                     # 請求年月(YYYYMM)
            self.office.office_number,                                  # 事業所番号
            self.municipality_code_zfill,                               # 市町村コード
            self.user.insured_number,                                   # 被保険者番号
            hogo_number,                                                # 公費負担者番号1
            recipient_number,                                           # 公費受給者番号1
            "",                                                         # 公費負担者番号2
            "",                                                         # 公費受給者番号2
            "",                                                         # 公費負担者番号3
            "",                                                         # 公費受給者番号3
            self.user.birth_date_value,                                 # 生年月日(YYYYMM)
            self.user.gender_disp,                                      # 性別区分(男1
            cert.convert_care_level,                                    # 介護度を国保連用コードに変換
            cert.certification_start,                                   # 適用開始日(YYYYMM)
            cert.certification_end,                                     # 適用終了日(YYYYMM)
            1,                                                          # 住居サービス作成区分
            self.user.care_manager.care_management_office_number,       # 居宅介護支援事業所番号

            0,                                                          # 開始年月日 月途中（通常0
            0,                                                          # 終了年月日 月途中（通常0
            "",                                                         # 23:中止理由（退所理由コード）
            cert.disp_benefit_rate,                                     # 保険給付率(90 80 70
            public_rate,                                                # 公費1の給付率
            0,                                                          # 公費2の給付率
            0,                                                          # 公費3の給付率
            self.record.total_units,                                    # 総請求単位数
            self.record.benefit_amount,                                 # 利用者負担合計額 保険請求（円換算
            self.record.user_share_amount,                              # 利用者負担額(超過分含む)生活保護0

            # 予備および公費
            "",                                                         # 公費1
            "",                                                         # 公費2
            "",                                                         # 公費3 利用者負担
            public_assist_units,                                        # 公費2 対象単位数
            public_amount,                                              # 公費2 請求額
            0,                                                          # 公費2 利用者負担
            "",                                                         # 公費3 対象単位数
            "",                                                         # 公費3 請求額
            #予備項目
            "",
            0,
            0,
            0,
            "",
            "",
            "",
            0,
            0,
        ]

    def _build_user_claim_details(self):
        """
        利用者1人分の 02 レコードを作る。

        """
        logger.info(f'詳細レコード作成: insured_number={self.user.insured_number} name={self.user.name}')
        rows = []
        for plan in self.plans:
            count = int(plan.get_total_count("actual"))
            unit = int(plan.unit)
            subtotal = (unit * count)
            logger.info(
                f"02明細: "
                f"service_code={plan.service_code}, "
                f"count={count}, "
                f"plan.unit={plan.unit}"
            )

            if self.user.get_public_assistance(self.year, self.month):
                public_count = count
                public_subtotal = subtotal
            else:   # 生活保護があるか
                public_count = 0
                public_subtotal = 0
            rows.append([ #プランごとの行
                self.RECORD_TYPE_DETAIL,                                # レコード識別子（固定: 2）
                self.count_up_row(),                                    # 全体連番
                self.record_set["claim_home_based_category"],           # サービス費用コード
                self.USER_RECORD_SERVICE,                               # サービス区分コード（固定: "02"）
                self.target_year_month,                                 # 請求年月(YYYYMM)
                self.office.office_number,                              # 事業所番号
                self.municipality_code_zfill,                           # 市町村コード
                self.user.insured_number,                               # 被保険者番号
                self.office.service_type_code,                          # サービス種類
                str(plan.service_code),                                 # サービスコード
                unit,                                                   # 単価
                count,                                                  # 回数
                # 公費が特定のサービスにのみ適用される場合
                public_count,                                           # 公費1対象回数
                0,                                                      # 公費2対象回数
                0,                                                      # 公費3対象回数
                subtotal,                                               # 小計単位数(単位*回数)
                public_subtotal,                                        # 公費1小計単位数
                0,                                                      # 公費2小計単位数
                0,                                                      # 公費3小計単位数
                f'\"\"',                                                # 摘要欄（サービス名などを記載する 基本空文字）
            ])
        for item in self.record.all_addons.values():
            addon_obj = item['addon']
            service_code = addon_obj.code
            if not addon_obj and addon_obj.insurance_type == 'self_pay':
                continue
            if addon_obj.type == 'rate':
                """ todo 加算の率対応 """
                logger.warning(f'加算の率対応は未実装です: {service_code} {addon_obj.service_name}')
                continue
            if addon_obj.type == 'unit' and addon_obj.unit is None:
                logger.error(f'加算単位が設定されていません: {service_code} {addon_obj.service_name}')
                raise ValueError(
                    f"加算単位が設定されていません: {service_code}"
                )

            count = int(len(item['days']))
            unit = int(addon_obj.unit)
            subtotal:int = unit * count
            logger.info(
                f"02明細(加算): "
                f"service_code={service_code}, "
                f"count={count}, "
                f"unit={unit}"
            )
            if self.user.get_public_assistance(self.year, self.month):
                public_count = count
                public_subtotal = subtotal
            else:  # 生活保護があるか
                public_count = 0
                public_subtotal = 0
            rows.append([  # 加算ごとの行
                self.RECORD_TYPE_DETAIL,                            # レコード識別子（固定: 2）
                self.count_up_row(),                                # 全体連番
                self.record_set["claim_home_based_category"],       # サービス費用コード
                self.USER_RECORD_SERVICE,                           # サービス区分コード（固定: "02"）
                self.target_year_month,                             # 請求年月(YYYYMM)
                self.office.office_number,                          # 事業所番号
                self.municipality_code_zfill,                       # 市町村コード
                self.user.insured_number,                           # 被保険者番号
                self.office.service_type_code,                      # サービス種類
                str(service_code),                                  # サービスコード
                addon_obj.unit,                                     # 単価
                count,                                              # 回数
                # 公費が適用される場合
                public_count,                                       # 公費1対象回数
                0,                                                  # 公費2対象回数
                0,                                                  # 公費3対象回数
                subtotal,                                           # 小計単位数(単位*回数)
                public_subtotal,                                    # 公費1小計単位数
                0,                                                  # 公費2小計単位数
                0,                                                  # 公費3小計単位数
                f'\"\"',                                            # 摘要欄（サービス名などを記載する 基本空文字）
            ])
        service_units = self.default_addon.get_unit(self.record.service_units)
        if self.user.get_public_assistance(self.year, self.month):
            public_count = 1
            public_subtotal = service_units
        else:
            public_count = 0
            public_subtotal = 0
        rows.append([  # デフォルトの行
            self.RECORD_TYPE_DETAIL,                                    # レコード識別子（固定: 2）
            self.count_up_row(),                                        # 全体連番
            self.record_set["claim_home_based_category"],               # サービス費用コード
            self.USER_RECORD_SERVICE,                                   # サービス区分コード（固定: "02"）
            self.target_year_month,                                     # 請求年月(YYYYMM)
            self.office.office_number,                                  # 事業所番号
            self.municipality_code_zfill,                               # 市町村コード
            self.user.insured_number,                                   # 被保険者番号
            self.office.service_type_code,                              # サービス種類
            str(self.default_addon.code),                               # サービスコード
            service_units,                                              # 単価
            1,                                                          # 回数(固定:1)
            public_count,                                               # 公費1対象回数
            0,                                                          # 公費2対象回数
            0,                                                          # 公費3対象回数
            service_units,                                              # 小計単位数(率の行 固定:0)
            public_subtotal,                                            # 公費1小計単位数
            0,                                                          # 公費2小計単位数
            0,                                                          # 公費3小計単位数
            f'\"\"',                                                    # 摘要欄（サービス名などを記載する 基本空文字）
        ])
        return rows
    def _build_user_claim_total(self):
        """
            利用者1人分の 10 レコードを作る。
            - サービス提供表で集計した結果を使う
        """
        logger.info(f'個人集計レコード作成: insured_number={self.user.insured_number} name={self.user.name}')
        if self.user.get_public_assistance(self.year, self.month): #生活保護があるか
            public_assist_units = self.record.total_units
            public_amount = self.record.public_amount
        else:
            public_assist_units = 0
            public_amount = 0
        return [
            self.RECORD_TYPE_DETAIL,                                    # レコード識別子（固定: 2）
            self.count_up_row(),                                        # 全体連番
            self.record_set["claim_home_based_category"],               # サービス費用コード(固定: 7111)
            self.USER_RECORD_TOTAL,                                     # サービス区分コード(固定: 10)
            self.target_year_month,                                     # 請求年月(YYYYMM)
            self.office.office_number,                                  # 事業所番号
            self.municipality_code_zfill,                               # 市町村コード(固定: 8桁)
            self.user.insured_number,                                   # 被保険者番号(10桁)
            self.office.service_type_code,                              # サービス種類( 15 or 78)
            self.record.actual_count,                                   # 給付日数 / 利用日数
            self.record.service_units,                                  # 計画単位数(基本報酬)
            self.record.service_units,                                  # 実績単位数
            self.default_addon.get_unit(self.record.service_units),     # 13:加算単位数（処遇改善加算 入浴加算など）

            # 以下は金額項目
            0,                                                          # todo 超過の単位数
            0,                                                          # 公費対象単位（なければ0
            self.record.total_units,                                    # 保険給付総請求単位数
            self.record.benefit_amount,                                 # 利用者負担合計額 保険請求（円換算
            self.record.public_amount,                                  # 公費請求（円換算
            self.record.user_share_amount,                              # 利用者負担額(超過分含む)生活保護0

            # 予備
            public_assist_units,                                        # 公費1 本人負担額 (生活保護の場合
            public_amount,                                              # 公費1 対象単位数
            0,                                                          # 公費2 請求額
            0,                                                          # 公費2 本人負担額
            0,                                                          # 公費3 対象単位数
            0,                                                          # 公費3 請求額
            0,                                                          # 公費3 本人負担額
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ]
    def _build_user_claim(self, record):
        """
         利用者のレコードから、01, 02, 10 の順に構築する。
            01: 利用者の認定・基本情報
            02: 利用者のサービス提供情報
            14: 利用者のサービス提供情報（特殊ケース）
            10: 利用者の集計情報
        """
        self.record = record
        self.plans = list(self.record.plans.all())
        self.user = self.record.user
        self.default_addon = self.office.default_service

        if not self.user.care_manager:
            raise ValueError(f'ケアマネジャーが設定されていない利用者={self.user.name}')
        # 01
        rows = [self._build_user_claim_basic()]

        # 02
        rows.extend(
            self._build_user_claim_details()
        )

        # 10
        rows.append(
            self._build_user_claim_total()
        )

        return rows

    def build_office_claim_end(self):
        logger.info('請求書情報：最終レコードの作成開始')
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
        logger.info(f'請求書情報：基本情報の作成開始:year={self.year} month={self.month} office={self.office.name}')
        rows = [self.build_office_claim_header()]

        # 2. 請求書明細情報
        rows.extend(
            self.build_office_claim_details()
        )
        logger.info('請求書情報：明細情報の作成完了')

        # 3. 利用者ごとの請求情報を作成し、仕様順に直す 1~3行
        for record in self.records:
            rows.extend(
                self._build_user_claim(record)
            )
        logger.info('請求書情報：利用者ごとの請求情報の作成完了')
        # 5. エンドの行
        rows.append(
            self.build_office_claim_end()
        )
        return rows