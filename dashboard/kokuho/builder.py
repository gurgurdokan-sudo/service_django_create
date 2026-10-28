from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from dashboard.models import ServiceMonthlyRecord
from dashboard.models.const import MEDIA_TYPE_INTERNET, get_claim_profile

import logging
logger = logging.getLogger(__name__)

# 摘要欄など「""」と出力したい空欄の目印（CsvExporter がそのまま書き出す）
QUOTED_EMPTY = '""'


class ClaimBuilder:
    # 共通編 p.7-8 レコード種別
    RECORD_TYPE_HEADER = 1          # コントロールレコード
    RECORD_TYPE_DETAIL = 2          # データレコード
    RECORD_TYPE_END = 3             # エンドレコード

    # サービス事業所編 7131 のレコード種別コード
    USER_RECORD_BASIC = '01'        # 基本情報
    USER_RECORD_SERVICE = '02'      # 明細情報
    USER_RECORD_TOTAL = '10'        # 集計情報

    INSURANCE_CLAIM = 1             # 共通編 p.37 保険・公費等区分 1:保険請求
    PUBLIC_CLAIM = 2                # 2:公費請求
    LAW_NUMBER_WELFARE = 12         # 法別番号 12:生活保護
    OLD_MEASURE_NONE = ''           # 旧措置入所者特例：様式第二は設定不要
    STOP_REASON_NONE = ''           # 中止理由：月途中中止時のみ設定（解説書 p.6 様式第二は○）

    def __init__(self, office, year, month, create_year=None, create_month=None):
        self.office = office
        self.year = year
        self.month = month
        self.target_year_month = f"{year}{month:02d}"            # サービス提供年月

        if create_year is None or create_month is None:
            next_month = date(year, month, 1) + relativedelta(months=1)
            create_year, create_month = next_month.year, next_month.month
        self.create_year_month = f"{create_year}{create_month:02d}"  # 処理対象年月（提出月）

        # 請求区分（データ種別・交換情報識別番号）をサービス種類から決める
        self.profile = get_claim_profile(self.office.service_type_code)

        # 単位数単価：整数2桁＋小数2桁（10.45円 → "1045"）共通編 p.42
        price = Decimal(str(self.office.unit_price))
        self.unit_price_code = f"{int((price * 100).quantize(Decimal('1'), ROUND_HALF_UP)):04d}"

        self.records = ServiceMonthlyRecord.objects.filter(
            office=office, date__year=year, date__month=month,
        ).select_related('user', 'user__care_manager')
        self.row = 0

    # ---------- 共通ヘルパー ----------
    def count_up_row(self):
        self.row += 1
        return self.row

    def _data_prefix(self, record_kind=None):
        """データレコード共通部：2, 通番, 交換情報識別番号[, レコード種別コード]"""
        prefix = [self.RECORD_TYPE_DETAIL, self.count_up_row(),
                  self.profile["detail_id"]]
        if record_kind:
            prefix.append(record_kind)
        return prefix

    def _insurer_number(self):
        """証記載保険者番号：6桁を8桁に0埋め（解説書 p.1-2）。
        TODO: 住所地特例等に備え、利用者の被保険者証の保険者番号を持たせて優先する。"""
        code = getattr(self.user, 'insurer_number', None) or self.office.municipality.municipality_code
        return str(code).zfill(8)

    @staticmethod
    def _rate_code(rate):
        """給付率 0.9 / 90 のどちらで保存されていても "90" を返す"""
        rate = float(rate)
        return str(int(round(rate * 100))) if rate <= 1 else str(int(round(rate)))

    @staticmethod
    def _service_item_code(code):
        """サービス項目コード（4桁）。"781344" のような6桁が来ても末尾4桁にする"""
        return str(code)[-4:].zfill(4)

    def _limit_units(self):
        """限度額管理対象単位数＝基本サービス＋単位数加算・減算（5612等の負値も含める）"""
        units = sum(int(p.unit) * int(p.get_total_count("actual")) for p in self.plans)
        for item in self.record.all_addons.values():
            addon = item['addon']
            if not addon or addon.insurance_type == 'self_pay' or addon.type == 'rate':
                continue
            if addon.unit is not None:
                units += int(addon.unit) * len(item['days'])
        return units

    def _rate_units(self):
        """処遇改善加算などの率加算：限度額管理対象単位数×率を四捨五入（get_unit 側で ROUND_HALF_UP）"""
        return self.default_addon.get_unit(self.limit_units) if self.default_addon else 0

    @staticmethod
    def _ins_units(r):
        return r.total_units - (r.over_units or 0)       # 限度超過分は保険対象外

    @staticmethod
    def _ins_cost(r):
        return r.total_cost - (r.over_cost or 0)

    @staticmethod
    def _ins_user_share(r):
        return (r.user_share_amount or 0) - (r.over_user_share or 0)

    # ---------- コントロールレコード（12列） ----------
    def build_office_claim_header(self, data_count=0):
        return [
            self.RECORD_TYPE_HEADER,                 # 1 レコード種別
            self.count_up_row(),                     # 2 レコード番号
            0,                                       # 3 ボリューム通番
            data_count,                              # 4 データレコード件数（build()で確定）
            self.profile['data_type'],               # 5 データ種別 711
            0,                                       # 6 福祉事務所特定番号
            0,                                       # 7 保険者番号
            self.office.office_number,               # 8 事業所番号
            0,                                       # 9 都道府県番号
            MEDIA_TYPE_INTERNET,                     # 10 媒体区分
            self.create_year_month,                  # 11 処理対象年月（提出月）
            0,                                       # 12 ファイル管理番号
        ]

    # ---------- 7111 請求書情報（20列） ----------
    def _claim_summary_row(self, ins_pub_kind, law_number, count, units, cost,
                           insurance_amount, public_amount, user_share):
        return [
            self.RECORD_TYPE_DETAIL, self.count_up_row(),
            self.profile['summary_id'],              # 1 交換情報識別番号 7111
            self.target_year_month,                  # 2 サービス提供年月
            self.office.office_number,               # 3 事業所番号
            ins_pub_kind,                            # 4 保険・公費等区分
            law_number,                              # 5 法別番号
            self.profile['claim_info_code'],         # 6 請求情報区分 01
            count, units, cost,                      # 7-9 件数・単位数・費用合計
            insurance_amount,                        # 10 保険請求額
            public_amount,                           # 11 公費請求額
            user_share,                              # 12 利用者負担
            0, 0, 0, 0, 0, 0,                        # 13-18 特定入所者介護サービス費等
        ]

    def build_office_claim_details(self):
        records = list(self.records)
        rows = [self._claim_summary_row(
            self.INSURANCE_CLAIM, 0, len(records),
            sum(self._ins_units(r) for r in records),
            sum(self._ins_cost(r) for r in records),
            sum(r.benefit_amount for r in records),
            sum(r.public_amount or 0 for r in records),
            sum(self._ins_user_share(r) for r in records),
        )]
        public = [r for r in records if r.user.get_public_assistance(self.year, self.month)]
        if public:
            rows.append(self._claim_summary_row(
                self.PUBLIC_CLAIM, self.LAW_NUMBER_WELFARE, len(public),
                sum(self._ins_units(r) for r in public),
                sum(self._ins_cost(r) for r in public),   # 修正：単位数ではなく費用合計
                0,                                         # 公費請求行の保険請求額
                sum(r.public_amount or 0 for r in public),
                0,                                         # 生保の本人負担（本人支払額がある場合は設定）
            ))
        return rows

    # ---------- 01 基本情報（2+56=58列） ----------
    def _build_user_claim_basic(self):
        cert = self.user.get_certificate(self.year, self.month)
        if not cert:
            raise ValueError(f"認定情報がありません: insured_number={self.user.insured_number}")
        if not cert.is_active:
            logger.warning(f'認定情報が無効です: insured_number={self.user.insured_number}')

        r, pa = self.record, self.public
        ins_units = self._ins_units(r)
        pub = (
            [pa.hogo_number, pa.recipient_number] if pa else ['', '']
        )
        pub1_totals = [ins_units, r.public_amount or 0, 0] if pa else [0, 0, 0]

        return self._data_prefix(self.USER_RECORD_BASIC) + [
            self.target_year_month,                      # 3 サービス提供年月
            self.office.office_number,                   # 4 事業所番号
            self._insurer_number(),                      # 5 証記載保険者番号
            self.user.insured_number,                    # 6 被保険者番号
            *pub,                                        # 7-8 公費1 負担者番号・受給者番号
            '', '',                                      # 9-10 公費2
            '', '',                                      # 11-12 公費3
            self.user.birth_date_value,                  # 13 生年月日 YYYYMMDD
            self.user.gender_disp,                       # 14 性別コード
            cert.convert_care_level,                     # 15 要介護状態区分コード
            self.OLD_MEASURE_NONE,                       # 16 旧措置入所者特例（追加）
            cert.certification_start,                    # 17 認定有効期間 開始 YYYYMMDD
            cert.certification_end,                      # 18 認定有効期間 終了 YYYYMMDD
            1,                                           # 19 居宅サービス計画作成区分 1:居宅介護支援事業所
            self.user.care_manager.care_management_office_number,  # 20 居宅介護支援事業所番号
            '',                                          # 21 開始年月日（月途中開始時のみ）
            '',                                          # 22 中止年月日（月途中中止時のみ）
            self.STOP_REASON_NONE,                       # 23 中止理由（通常は空欄）
            '', '',                                      # 24-25 入所（院）年月日・退所（院）年月日
            0, 0,                                        # 26-27 入所（院）実日数・外泊日数（現行ソフトに合わせ0）
            '',                                          # 28 退所（院）後の状態
            self._rate_code(cert.benefit_rate),          # 29 保険給付率
            100 if pa else 0,                            # 30 公費1給付率
            0, 0,                                        # 31-32 公費2・3給付率
            ins_units,                                   # 33 保険 サービス単位数
            r.benefit_amount,                            # 34 保険 請求額
            self._ins_user_share(r),                     # 35 保険 利用者負担額
            '', '', '',                                  # 36-38 緊急時・特定診療・特定入所者
            *pub1_totals,                                # 39-41 公費1 単位数・請求額・本人負担額
            '', '', '',                                  # 42-44 公費1 緊急時・特定診療・特定入所者
            0, 0, 0,                                     # 45-47 公費2 単位数・請求額・本人負担額
            '', '', '',                                  # 48-50 公費2 緊急時・特定診療・特定入所者
            0, 0, 0,                                     # 51-53 公費3 単位数・請求額・本人負担額
            '', '', '',                                  # 54-56 公費3 緊急時・特定診療・特定入所者
        ]

    # ---------- 02 明細情報（2+18=20列） ----------
    def _detail_row(self, service_item_code, unit, count, subtotal):
        pub_count, pub_units = (count, subtotal) if self.public else (0, 0)
        return self._data_prefix(self.USER_RECORD_SERVICE) + [
            self.target_year_month,                      # 3 サービス提供年月
            self.office.office_number,                   # 4 事業所番号
            self._insurer_number(),                      # 5 証記載保険者番号
            self.user.insured_number,                    # 6 被保険者番号
            self.office.service_type_code,               # 7 サービス種類コード
            self._service_item_code(service_item_code),  # 8 サービス項目コード（4桁）
            unit,                                        # 9 単位数（4桁）
            count,                                       # 10 日数・回数
            pub_count, 0, 0,                             # 11-13 公費1-3 対象日数・回数
            subtotal,                                    # 14 サービス単位数
            pub_units, 0, 0,                             # 15-17 公費1-3 対象サービス単位数
            QUOTED_EMPTY,                                # 18 摘要（現行ソフトに合わせ "" を出力）
        ]

    def _build_user_claim_details(self):
        rows = []
        basic_detail_totals = {}

        # CSV明細上のサービス項目コード・単位数が同じ基本Planを集約する
        for plan in self.plans:
            count = int(plan.get_total_count("actual"))
            if count <= 0:
                continue
            unit = int(plan.unit)
            service_item_code = self._service_item_code(plan.service_code)
            key = (service_item_code, unit)
            basic_detail_totals[key] = basic_detail_totals.get(key, 0) + count

        for (service_item_code, unit), count in basic_detail_totals.items():
            rows.append(
                self._detail_row(
                    service_item_code,
                    unit,
                    count,
                    unit * count,
                )
            )

        for item in self.record.all_addons.values():
            addon = item['addon']
            if not addon or addon.insurance_type == 'self_pay':
                continue
            if addon.type == 'rate':
                logger.warning(f'率加算は下の行で出力: {addon.code}')
                continue
            if addon.unit is None:
                raise ValueError(f"加算単位が設定されていません: {addon.code}")
            count = len(item['days'])
            rows.append(self._detail_row(addon.code, int(addon.unit), count, int(addon.unit) * count))

        if self.default_addon:  # 処遇改善加算などの率加算
            units = self._rate_units()  # 減算後の単位数に率を掛ける
            if units > 0:
                if units > 9999:
                    logger.warning(f'02の単位数欄は4桁です: {units}')
                rows.append(self._detail_row(self.default_addon.code, units, 1, units))
        return rows

    # ---------- 10 集計情報（2+38=40列） ----------
    def _build_user_claim_total(self):
        r, pa = self.record, self.public
        ins_units = self._ins_units(r)
        rate_units = self._rate_units()
        if self.limit_units + rate_units != r.total_units:
            logger.warning(
                f'10の単位数が月次記録と一致しません: insured_number={self.user.insured_number} '
                f'計算={self.limit_units + rate_units} 記録={r.total_units}（ServiceSheetCalculatorの修正を確認）'
            )
        pub1 = [ins_units, r.public_amount or 0, 0] if pa else [0, 0, 0]

        return self._data_prefix(self.USER_RECORD_TOTAL) + [
            self.target_year_month,                      # 3 サービス提供年月
            self.office.office_number,                   # 4 事業所番号
            self._insurer_number(),                      # 5 証記載保険者番号
            self.user.insured_number,                    # 6 被保険者番号
            self.office.service_type_code,               # 7 サービス種類コード
            r.actual_count,                              # 8 サービス実日数
            self.limit_units,                            # 9 計画単位数（減算込み）
            self.limit_units,                            # 10 限度額管理対象単位数（減算込み）
            rate_units,                                  # 11 限度額管理対象外単位数
            0, 0,                                        # 12-13 短期入所 計画日数・実日数
            ins_units,                                   # 14 保険 単位数合計
            self.unit_price_code,                        # 15 保険 単位数単価（追加）
            r.benefit_amount,                            # 16 保険 請求額
            self._ins_user_share(r),                     # 17 保険 利用者負担額
            *pub1,                                       # 18-20 公費1 単位数合計・請求額・本人負担額
            0, 0, 0,                                     # 21-23 公費2
            0, 0, 0,                                     # 24-26 公費3
            0, 0, 0,                                     # 27-29 保険分出来高医療費
            0, 0, 0,                                     # 30-32 公費1分出来高医療費
            0, 0, 0,                                     # 33-35 公費2分出来高医療費
            0, 0, 0,                                     # 36-38 公費3分出来高医療費
        ]

    def _build_user_claim(self, record):
        self.record = record
        self.plans = record.plans.all()                  # 修正：values_list() をやめる
        self.user = record.user
        self.public = self.user.get_public_assistance(self.year, self.month)
        self.default_addon = self.office.default_service
        self.limit_units = self._limit_units()
        if not self.user.care_manager:
            raise ValueError(f'ケアマネジャーが設定されていない利用者={self.user.name}')

        rows = [self._build_user_claim_basic()]
        rows.extend(self._build_user_claim_details())
        rows.append(self._build_user_claim_total())
        return rows

    # ---------- エンドレコード（2列） ----------
    def build_office_claim_end(self):
        return [self.RECORD_TYPE_END, self.count_up_row()]

    def build(self):
        self.row = 0
        header = self.build_office_claim_header()
        rows = [header]
        rows.extend(self.build_office_claim_details())
        for record in self.records:
            rows.extend(self._build_user_claim(record))
        header[3] = len(rows) - 1                        # データレコード件数（1と3は除く）
        rows.append(self.build_office_claim_end())
        return rows