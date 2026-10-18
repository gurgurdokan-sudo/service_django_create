from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def validate_year_month(value):
    """年月フォーマット（YYYYMM）の検証"""
    value = str(value)
    if len(value) != 6 or not value.isdigit():
        return False
    try:
        datetime.strptime(value, "%Y%m")
    except ValueError:
        return False
    return True
def is_digits(value, length=None):
    """数字のみか（length 指定時は桁数も確認）"""
    value = str(value)
    return value.isdigit() and (length is None or len(value) == length)
def to_int(value):
    """整数に変換（減算の負数も可）。変換できなければ None"""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None

class ClaimValidator:
    """
    国保連請求データ（CSV出力前の配列）の検証を行うクラス
    Builder の戻り値・CSV を読み戻した値のどちらでも検証できるよう、値は文字列に揃えて比較する
    """

    # レコード種別コード
    REC_HEADER = '1'
    REC_DETAIL = '2'
    REC_END = '3'

    # 交換情報識別番号
    ID_SUMMARY = '7111'
    ID_USER = '7131'

    # 7131 のレコード種別（基本、明細、集計）
    KIND_BASIC = '01'
    KIND_SERVICE = '02'
    KIND_TOTAL = '10'

    # 7111 保険・公費等区分
    INSURANCE_CLAIM = '1'
    PUBLIC_CLAIM = '2'

    # 各レコードのCSV全列数（共通の「2,レコード番号」を含む）
    LEN_HEADER = 12
    LEN_END = 2
    LEN_SUMMARY = 20
    LEN_USER = {KIND_BASIC: 58, KIND_SERVICE: 20, KIND_TOTAL: 40}

    # ---- 列番号（0始まり） ----
    # コントロールレコード
    H_DATA_COUNT, H_OFFICE, H_PROCESS_YM = 3, 7, 10
    # 7111 請求書情報
    S_YM, S_OFFICE, S_KIND, S_COUNT, S_UNITS, S_INS_AMOUNT = 3, 4, 5, 8, 9, 11
    # 7131 共通
    U_KIND, U_YM, U_OFFICE, U_INSURER, U_INSURED = 3, 4, 5, 6, 7
    # 01 基本情報
    B_INS_UNITS, B_INS_AMOUNT = 34, 35
    # 02 明細情報
    D_ITEM_CODE, D_UNITS = 9, 15
    # 10 集計情報
    T_LIMIT_UNITS, T_NON_LIMIT_UNITS, T_INS_UNITS, T_INS_AMOUNT = 11, 12, 15, 17

    def __init__(self):
        self._reset()

    def _reset(self):
        """validate() のたびに状態を初期化する"""
        self.errors = []
        self.header_seen = False
        self.end_seen = False
        self.office_number = None
        self.process_year_month = None
        self.target_year_month = None
        self.header_data_count = None
        self.expected_seq = 1
        self.detail_count = 0
        self.no_header_reported = False

        # 7111（保険請求行）と利用者合計の突き合わせ用
        self.summary = None
        self.summary_missing_reported = False
        self.user_started = False
        self.user_count = 0
        self.total_ins_units = 0
        self.total_ins_amount = 0

        # 利用者レコードの並び順管理用（None -> '01' -> '02'(複数可) -> '10'）
        self.current_user_id = None
        self.current_user_state = None
        self.user_basic = None          # 01の（保険単位数, 保険請求額）
        self.user_service_units = 0     # 02のサービス単位数の合計
        self.user_has_error = False     # 列数エラーがあれば合計チェックをしない

    def _add_error(self, row_idx, message):
        msg = f"行 {row_idx + 1}: {message}"
        logger.error(msg)
        self.errors.append(msg)

    # ==========================================
    # 入口
    # ==========================================
    def validate(self, rows):
        self._reset()

        if not isinstance(rows, (list, tuple)) or not rows:
            self._add_error(0, "請求対象のデータが存在しない、または配列ではありません。")
            return False, self.errors

        last_index = len(rows) - 1
        for index, row in enumerate(rows):
            if not isinstance(row, (list, tuple)) or len(row) == 0:
                self._add_error(index, "行が空、または不正な形式です。")
                self.expected_seq += 1
                continue

            # 要素はすべて文字列化して比較・検証する（型の不一致を防止）
            r = [str(col).strip() if col is not None else "" for col in row]
            rec_type = r[0]

            if index == 0 and rec_type != self.REC_HEADER:
                self._add_error(index, "先頭行がコントロールレコード（1）ではありません。")

            self._check_seq(index, r)

            if rec_type == self.REC_HEADER:
                self._validate_header(index, r)
            elif rec_type == self.REC_DETAIL:
                self._validate_detail(index, r)
            elif rec_type == self.REC_END:
                self._validate_end(index, r, last_index)
            else:
                self._add_error(index, f"未知のレコード種別（先頭列）です: {rec_type}")

        self._finalize(last_index)

        if self.errors:
            return False, self.errors
        return True, []

    # ==========================================
    # 共通チェック
    # ==========================================
    def _check_seq(self, index, r):
        """通番の連続性。ずれたら実際の値に合わせ直し、以降にエラーを連鎖させない"""
        seq = r[1] if len(r) > 1 else ""
        if seq != str(self.expected_seq):
            self._add_error(index, f"レコード番号（通番）が連続していません。期待値: {self.expected_seq}, 実際: {seq}")
            if seq.isdigit():
                self.expected_seq = int(seq)
        self.expected_seq += 1

    def _check_office(self, index, label, value):
        if self.office_number and value != self.office_number:
            self._add_error(index, f"{label}: 事業所番号がヘッダーと一致しません: {value}")

    # ==========================================
    # コントロールレコード (1)
    # ==========================================
    def _validate_header(self, index, r):
        if self.header_seen:
            self._add_error(index, "コントロールレコード（1）が複数あります。")
            return
        self.header_seen = True

        if index != 0:
            self._add_error(index, "コントロールレコード（1）が先頭行にありません。")
        if len(r) != self.LEN_HEADER:
            self._add_error(index, f"ヘッダー行の列数が不正です。期待値: {self.LEN_HEADER}, 実際: {len(r)}")
            return

        self.office_number = r[self.H_OFFICE]
        if not is_digits(self.office_number, 10):
            self._add_error(index, f"事業所番号は10桁の数字です: {self.office_number}")

        count = r[self.H_DATA_COUNT]
        if is_digits(count):
            self.header_data_count = int(count)
        else:
            self._add_error(index, f"データレコード件数が数字ではありません: {count}")

        if validate_year_month(r[self.H_PROCESS_YM]):
            self.process_year_month = r[self.H_PROCESS_YM]
        else:
            self._add_error(index, f"処理対象年月（提出月）のフォーマットエラーです: {r[self.H_PROCESS_YM]}")

    # ==========================================
    # データレコード (2)
    # ==========================================
    def _validate_detail(self, index, r):
        self.detail_count += 1

        if not self.header_seen:
            if not self.no_header_reported:  # 1回だけ出す
                self._add_error(index, "ヘッダーより前にデータレコードが存在します。")
                self.no_header_reported = True
            return
        if self.end_seen:
            self._add_error(index, "エンドレコードより後にデータレコードが存在します。")
        if len(r) < 3:
            self._add_error(index, "交換情報識別番号が存在しません。")
            return

        exchange_id = r[2]
        if exchange_id == self.ID_SUMMARY:
            self._validate_summary(index, r)
        elif exchange_id == self.ID_USER:
            self._validate_user(index, r)
        else:
            self._add_error(index, f"未知の交換情報識別番号です: {exchange_id}")

    # --- 7111 請求書情報 ---
    def _validate_summary(self, index, r):
        if self.user_started:
            self._add_error(index, "7111: 請求書情報が明細書情報（7131）より後にあります。")
        if len(r) != self.LEN_SUMMARY:
            self._add_error(index, f"7111行の列数が不正です。期待値: {self.LEN_SUMMARY}, 実際: {len(r)}")
            return

        ym = r[self.S_YM]
        if not validate_year_month(ym):
            self._add_error(index, f"7111: サービス提供年月のエラーです: {ym}")
        elif self.target_year_month and ym != self.target_year_month:
            self._add_error(index, f"7111: サービス提供年月が他の7111行と異なります: {ym}")
        else:
            self.target_year_month = ym
            if self.process_year_month and ym >= self.process_year_month:
                self._add_error(index, f"7111: サービス提供年月 {ym} が処理対象年月 {self.process_year_month} 以降です。")

        self._check_office(index, "7111", r[self.S_OFFICE])

        kind = r[self.S_KIND]
        if kind == self.INSURANCE_CLAIM:
            if self.summary is not None:
                self._add_error(index, "7111: 保険請求行が複数あります。")
                return
            self.summary = {
                "index": index,
                "count": to_int(r[self.S_COUNT]),
                "units": to_int(r[self.S_UNITS]),
                "amount": to_int(r[self.S_INS_AMOUNT]),
            }
        elif kind != self.PUBLIC_CLAIM:
            self._add_error(index, f"7111: 保険・公費等区分が不正です: {kind}")

    # --- 7131 明細書情報 ---
    def _validate_user(self, index, r):
        if len(r) <= self.U_KIND:
            self._add_error(index, "7131: レコード種別（01/02/10）が存在しません。")
            return

        kind = r[self.U_KIND]
        expected_len = self.LEN_USER.get(kind)
        if expected_len is None:
            self._add_error(index, f"7131: 未知のレコード種別です: {kind}")
            return

        if not self.user_started:
            self.user_started = True
            if self.summary is None and not self.summary_missing_reported:
                self._add_error(index, "7131より前に7111（保険請求）行がありません。")
                self.summary_missing_reported = True

        # 並び順は列数が不正でも確認する（後続行へのエラー連鎖を防ぐ）
        user_id = r[self.U_INSURED] if len(r) > self.U_INSURED else "不明"
        self._check_user_order(index, kind, user_id)

        if len(r) != expected_len:
            self._add_error(index, f"7131({kind})行の列数が不正です。期待値: {expected_len}, 実際: {len(r)}")
            self.user_has_error = True
            return

        # 年月・事業所・番号の形式
        ym = r[self.U_YM]
        if not validate_year_month(ym):
            self._add_error(index, f"7131({kind}): サービス提供年月のエラーです: {ym}")
        elif self.target_year_month and ym != self.target_year_month:
            self._add_error(index, f"7131({kind}): サービス提供年月が7111と一致しません: {ym}")
        self._check_office(index, f"7131({kind})", r[self.U_OFFICE])
        if not is_digits(r[self.U_INSURER], 8):
            self._add_error(index, f"7131({kind}): 証記載保険者番号は8桁の数字です: {r[self.U_INSURER]}")
        if not is_digits(user_id, 10):
            self._add_error(index, f"7131({kind}): 被保険者番号は10桁の数字です: {user_id}")

        if kind == self.KIND_BASIC:
            self._validate_basic(index, r)
        elif kind == self.KIND_SERVICE:
            self._validate_service(index, r)
        else:
            self._validate_total(index, r)

    def _check_user_order(self, index, kind, user_id):
        """利用者単位の並び順チェック (01 -> 02(0件以上) -> 10)"""
        state = self.current_user_state
        if kind == self.KIND_BASIC:
            if state in (self.KIND_BASIC, self.KIND_SERVICE):
                self._add_error(index, f"前の利用者 {self.current_user_id} の集計行(10)が無いまま、新しい基本情報(01)が開始されました。")
            self.current_user_id = user_id
            self.current_user_state = self.KIND_BASIC
            self.user_basic = None
            self.user_service_units = 0
            self.user_has_error = False
            self.user_count += 1
            return

        if state not in (self.KIND_BASIC, self.KIND_SERVICE):
            self._add_error(index, f"7131({kind}): 基本情報(01)が存在しない、または順番が不正です。被保険者番号: {user_id}")
            self.user_has_error = True
        elif self.current_user_id != user_id:
            self._add_error(index, f"7131({kind}): 被保険者番号が01と一致しません。期待値: {self.current_user_id}, 実際: {user_id}")
            self.user_has_error = True
        self.current_user_state = kind

    def _validate_basic(self, index, r):
        units, amount = to_int(r[self.B_INS_UNITS]), to_int(r[self.B_INS_AMOUNT])
        if units is None or amount is None:
            self._add_error(index, "7131(01): 保険の単位数・請求額が数値ではありません。")
            self.user_has_error = True
            return
        self.user_basic = (units, amount)

    def _validate_service(self, index, r):
        if not is_digits(r[self.D_ITEM_CODE], 4):
            self._add_error(index, f"7131(02): サービス項目コードは4桁の数字です: {r[self.D_ITEM_CODE]}")
        units = to_int(r[self.D_UNITS])
        if units is None:
            self._add_error(index, f"7131(02): サービス単位数が数値ではありません: {r[self.D_UNITS]}")
            self.user_has_error = True
            return
        self.user_service_units += units

    def _validate_total(self, index, r):
        limit = to_int(r[self.T_LIMIT_UNITS])
        non_limit = to_int(r[self.T_NON_LIMIT_UNITS])
        ins_units = to_int(r[self.T_INS_UNITS])
        ins_amount = to_int(r[self.T_INS_AMOUNT])
        if None in (limit, non_limit, ins_units, ins_amount):
            self._add_error(index, "7131(10): 単位数・請求額に数値でない値があります。")
            self.user_has_error = True
            return

        self.total_ins_units += ins_units
        self.total_ins_amount += ins_amount

        if self.user_has_error:
            return  # 01/02 に不備がある利用者は合計チェックを省略（エラー連鎖を防ぐ）

        if self.user_service_units != limit + non_limit:
            self._add_error(index, f"7131(10): 02の単位数合計 {self.user_service_units} と、10の限度額管理対象＋対象外 {limit + non_limit} が一致しません。")
        if self.user_basic:
            basic_units, basic_amount = self.user_basic
            if basic_units != ins_units:
                self._add_error(index, f"7131(10): 保険単位数合計 {ins_units} が01の {basic_units} と一致しません。")
            if basic_amount != ins_amount:
                self._add_error(index, f"7131(10): 保険請求額 {ins_amount} が01の {basic_amount} と一致しません。")

    # ==========================================
    # エンドレコード (3)
    # ==========================================
    def _validate_end(self, index, r, last_index):
        if self.end_seen:
            self._add_error(index, "エンドレコード（3）が複数あります。")
            return
        self.end_seen = True
        if index != last_index:
            self._add_error(index, "エンドレコード（3）が最終行にありません。")
        if len(r) != self.LEN_END:
            self._add_error(index, f"エンド行の列数が不正です。期待値: {self.LEN_END}, 実際: {len(r)}")

    # ==========================================
    # 全行を読んだ後のチェック
    # ==========================================
    def _finalize(self, last_index):
        if not self.end_seen:
            self._add_error(last_index, "エンドレコード（3）がありません。")

        if self.header_data_count is not None and self.detail_count != self.header_data_count:
            self._add_error(last_index, f"データレコード件数が一致しません。ヘッダー定義: {self.header_data_count}, 実際の件数: {self.detail_count}")

        if self.current_user_state in (self.KIND_BASIC, self.KIND_SERVICE):
            self._add_error(last_index, f"最終利用者の集計行(10)が欠落しています。被保険者番号: {self.current_user_id}")

        if self.summary is None:
            if self.header_seen and not self.summary_missing_reported:
                self._add_error(last_index, "7111（保険請求）行がありません。")
            return

        s, idx = self.summary, self.summary["index"]
        if s["count"] != self.user_count:
            self._add_error(idx, f"7111: 件数 {s['count']} が利用者数（01の行数）{self.user_count} と一致しません。")
        if s["units"] != self.total_ins_units:
            self._add_error(idx, f"7111: 単位数 {s['units']} が10行の保険単位数合計 {self.total_ins_units} と一致しません。")
        if s["amount"] != self.total_ins_amount:
            self._add_error(idx, f"7111: 保険請求額 {s['amount']} が10行の保険請求額合計 {self.total_ins_amount} と一致しません。")