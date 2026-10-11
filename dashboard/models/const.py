LEVEL_CHOICES = [
    # ('要支援1', '要支援1'),
    # ('要支援2', '要支援2'),
    ('要介護1', '要介護1'),
    ('要介護2', '要介護2'),
    ('要介護3', '要介護3'),
    ('要介護4', '要介護4'),
    ('要介護5', '要介護5'),
]
BENEFIT_RATE_CHOICES = [
    (0.9, "給付率90%（1割負担）"),
    (0.8, "給付率80%（2割負担）"),
    (0.7, "給付率70%（3割負担）"),
]

STAY_TIME_CHOICES = [
    ('<3', '3時間以下'),
    ('3-4', '3以上-4未満'),
    ('4-5', '4以上-5未満'),
    ('5-6', '5以上-6未満'),
    ('6-7', '6以上-7未満'),
    ('7-8', '7以上-8未満'),
    ('8-9', '8以上-9未満')
]

# 所属の市町村（地域区分）で単位数単価が変化
UNIT_PRICE_TABLE = {7: 11.40, 6: 10.90, 5: 10.45, 4: 10.25, 3: 10.15, 2: 10.10, 1: 10.00}

# ==================================================
# サービス種類（国保連のサービス種類コード 2桁）
#   規模（通常・大規模Ⅰ・Ⅱ）はサービス種類ではなく
#   サービスコード（項目コード4桁）で区別する
# ==================================================
SERVICE_TYPE_CODE = 78  # 既定値（Office.service_type_code の default）

SERVICE_TYPES = {
    15: {"name": "通所介護",           "profile": "care_home"},
    78: {"name": "地域密着型通所介護", "profile": "care_home"},
}
SERVICE_TYPE_CHOICES = [(code, v["name"]) for code, v in SERVICE_TYPES.items()]

# 通所介護（15）の事業所規模。サービスコード表の選択に使う
FACILITY_SCALE_CHOICES = [
    ("normal", "通常規模"),
    ("large1", "大規模Ⅰ"),
    ("large2", "大規模Ⅱ"),
]

# ==================================================
# 国保連IF 請求区分（共通編 p.7, p.37, p.50 / サービス事業所編 p.15-）
#   data_type        : コントロールレコードのデータ種別（3桁）
#   summary_id       : 請求書情報の交換情報識別番号
#   detail_id        : 明細書情報の交換情報識別番号（01/02/10 行）
#   claim_info_code  : 請求情報区分コード
# ==================================================
MEDIA_TYPE_INTERNET = 7  # 媒体区分 7:伝送（インターネット）

CLAIM_PROFILES = {
    "care_home": {
        "name": "介護給付 居宅サービス（様式第二）",
        "data_type": "711",
        "summary_id": "7111",
        "detail_id": "7131",
        "claim_info_code": "01",
    },
    "preventive_home": {
        "name": "介護予防サービス（様式第二の二）",
        "data_type": "711",
        "summary_id": "7111",
        "detail_id": "7132",
        "claim_info_code": "01",
    },
    "comprehensive": {
        "name": "介護予防・日常生活支援総合事業（様式第二の三）",
        "data_type": "71R",
        "summary_id": "7113",
        "detail_id": "71R1",
        "claim_info_code": "05",
    },
}

# ClaimBuilder が項目レイアウトまで実装済みの区分
SUPPORTED_CLAIM_PROFILES = {"care_home"}


def get_claim_profile(service_type_code):
    """サービス種類コードから請求区分を返す。未対応なら ValueError"""
    service = SERVICE_TYPES.get(int(service_type_code))
    if not service:
        raise ValueError(f"未登録のサービス種類コードです: {service_type_code}")
    key = service["profile"]
    if key not in SUPPORTED_CLAIM_PROFILES:
        raise ValueError(f"請求区分 {key} のCSV出力は未対応です")
    return {"key": key, **CLAIM_PROFILES[key]}