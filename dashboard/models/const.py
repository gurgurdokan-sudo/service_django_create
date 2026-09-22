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
SERVICE_TYPE_CHOICES = [
    (78, "地域密着型通所介護"),
    (79, "通所介護（通常規模）"),
    (80, "通所介護（大規模Ⅰ）"),
    (81, "通所介護（大規模Ⅱ）"),
]
# 所属の市町村で率が変化
UNIT_PRICE_TABLE = {7: 11.40, 6: 10.90, 5: 10.45, 4: 10.25, 3: 10.15, 2: 10.10, 1: 10.00}

DATA_TYPE_CARE_INSURANCE = 7
ITEM_NUMBER =77
CLAIM_CATEGORY = 711
CLAIM_DETAIL_CATEGORY = 7111
CLAIM_HOME_BASED_CATEGORY = 7131

# 通所介護事務所
SERVICE_TYPE_CODE = 78 #地域密着型通所介護

DATA_SET_CLAM ={    
    SERVICE_TYPE_CODE: {  # 地域密着型通所介護
        "item_number": ITEM_NUMBER,
        "claim_category": CLAIM_CATEGORY,
        "detail_category": CLAIM_DETAIL_CATEGORY,
        "record_name": "地域密着型　介護給付費請求書情報",
        "claim_home_based_category":CLAIM_HOME_BASED_CATEGORY
    },
    79: { #今後必要なら追加
        "item_number": 78,
        "claim_category": 713,
        "detail_category": CLAIM_HOME_BASED_CATEGORY,
        "record_name": "通常規模 介護給付費明細書情報",
        "claim_home_based_category":CLAIM_HOME_BASED_CATEGORY #?
    },
    80: {
        "item_number": 79,
        "claim_category": 714,
        "detail_category": 7141,
        "record_name": "大規模Ⅰ 介護給付費摘要情報",
        "claim_home_based_category":CLAIM_HOME_BASED_CATEGORY #?
    },
}