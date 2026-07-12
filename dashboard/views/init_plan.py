from dashboard.models import ServiceMaster
from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from dashboard.models import AddOnService

def init_plan(request):
    AddOnService.objects.all().delete()
    services = [
        AddOnService(code='0',type='unit', service_name='値引き', price=-1000, unit=0, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='時間サービス', price=1000, unit=0, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='昼食代', price=690, unit=0, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='おやつ代', price=150, unit=0, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='洗濯代', price=120, unit=0, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='教養娯楽費', price=50, unit=0, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='パット代', price=100, unit=0, category='消耗品', is_tax=True, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='キャンセル料', price=1000, unit=0, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='夕食代', price=690, unit=0, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='時間サービス', price=1500, unit=0, category='自費', is_tax=True, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='宿泊費', price=6800, unit=0, category='宿泊', is_tax=True, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='夕食代', price=690, unit=0, category='食費', is_tax=True, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
        AddOnService(code='0',type='unit', service_name='捕食', price=150, unit=0, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
        AddOnService(code='6107',type='rate', rate=0.09, service_name='通所介護処遇改善加算Ⅱ', unit=0, category='通所介護',insurance_type='insurance',apply_unit='monthly'),
        # 延長・感染症・災害（所定単位数に対する％加算・減算は単位を0として登録）
        AddOnService(code='6600',type='rate', service_name='通所介護感染症災害3％加算', unit=0, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6601', service_name='通所介護延長加算1', unit=50, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6602', service_name='通所介護延長加算2', unit=100, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6603', service_name='通所介護延長加算3', unit=150, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6604', service_name='通所介護延長加算4', unit=200, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6605', service_name='通所介護延長加算5', unit=250, category='通所介護', insurance_type='insurance', apply_unit='per_service'),

        # 共生型サービス減算（％減算のため単位0）
        AddOnService(code='6364', service_name='通所介護共生型サービス生活介護', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='6365', service_name='通所介護共生型サービス自立訓練', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='6366', service_name='通所介護共生型サービス児童発達支援', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='6367', service_name='通所介護共生型サービス放課後等デイ', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),

        # 基本加算・入浴・中重度
        AddOnService(code='6350', service_name='通所介護生活相談員配置等加算', unit=13, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='8110', service_name='通所介護中山間地域等提供加算', unit=0, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='5301', service_name='通所介護入浴介助加算Ⅰ', unit=40, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='5303', service_name='通所介護入浴介助加算Ⅱ', unit=55, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='5306', service_name='通所介護中重度者ケア体制加算', unit=45, category='通所介護', insurance_type='insurance', apply_unit='per_day'),

        # 生活機能向上・個別機能訓練
        AddOnService(code='4001', service_name='通所介護生活機能向上連携加算Ⅰ', unit=100, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='4002', service_name='通所介護生活機能向上連携加算Ⅱ1', unit=200, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='4003', service_name='通所介護生活機能向上連携加算Ⅱ2', unit=100, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='5051', service_name='通所介護個別機能訓練加算Ⅰ1', unit=56, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='5053', service_name='通所介護個別機能訓練加算Ⅰ2', unit=76, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='5052', service_name='通所介護個別機能訓練加算Ⅱ', unit=20, category='通所介護', insurance_type='insurance', apply_unit='monthly'),

        # ADL・認知症・若年性
        AddOnService(code='6338', service_name='通所介護ADL維持等加算Ⅰ', unit=30, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='6339', service_name='通所介護ADL維持等加算Ⅱ', unit=60, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='5305', service_name='通所介護認知症加算', unit=60, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='6109', service_name='通所介護若年性認知症受入加算', unit=60, category='通所介護', insurance_type='insurance', apply_unit='per_day'),

        # 栄養・口腔・科学的介護
        AddOnService(code='6116', service_name='通所介護栄養アセスメント加算', unit=50, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='5605', service_name='通所介護栄養改善加算', unit=200, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='6202', service_name='通所介護口腔栄養スクリーニング加算Ⅰ', unit=20, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6201', service_name='通所介護口腔栄養スクリーニング加算Ⅱ', unit=5, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='5606', service_name='通所介護口腔機能向上加算Ⅰ', unit=150, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='5608', service_name='通所介護口腔機能向上加算Ⅱ', unit=160, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
        AddOnService(code='6361', service_name='通所介護科学的介護推進体制加算', unit=40, category='通所介護', insurance_type='insurance', apply_unit='monthly'),

        # 減算
        AddOnService(code='5611', service_name='通所介護同一建物減算', unit=-94, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
        AddOnService(code='5612', service_name='通所介護送迎減算', unit=-47, category='通所介護', insurance_type='insurance', apply_unit='per_service'),

        # サービス提供体制加算
        AddOnService(code='6099', service_name='通所介護サービス提供体制加算Ⅰ', unit=22, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6100', service_name='通所介護サービス提供体制加算Ⅱ', unit=18, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
        AddOnService(code='6102', service_name='通所介護サービス提供体制加算Ⅲ', unit=6, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    ]

    AddOnService.objects.bulk_create(services)

    ServiceMaster.objects.all().delete()
    a = [
        # 地域密着型通所介護（種類コード：78）

        # 3時間以上4時間未満 (3-4)
        ServiceMaster(service_code='1141', service_name='地域通所介護１１', unit=416, stay_time_category='3-4', care_level='要介護1'),
        ServiceMaster(service_code='1142', service_name='地域通所介護１２', unit=478, stay_time_category='3-4', care_level='要介護2'),
        ServiceMaster(service_code='1143', service_name='地域通所介護１３', unit=540, stay_time_category='3-4', care_level='要介護3'),
        ServiceMaster(service_code='1144', service_name='地域通所介護１４', unit=600, stay_time_category='3-4', care_level='要介護4'),
        ServiceMaster(service_code='1145', service_name='地域通所介護１５', unit=663, stay_time_category='3-4', care_level='要介護5'),

        # 4時間以上5時間未満 (4-5)
        ServiceMaster(service_code='1241', service_name='地域通所介護２１', unit=436, stay_time_category='4-5', care_level='要介護1'),
        ServiceMaster(service_code='1242', service_name='地域通所介護２２', unit=501, stay_time_category='4-5', care_level='要介護2'),
        ServiceMaster(service_code='1243', service_name='地域通所介護２３', unit=566, stay_time_category='4-5', care_level='要介護3'),
        ServiceMaster(service_code='1244', service_name='地域通所介護２４', unit=631, stay_time_category='4-5', care_level='要介護4'),
        ServiceMaster(service_code='1245', service_name='地域通所介護２５', unit=696, stay_time_category='4-5', care_level='要介護5'),

        # 5時間以上6時間未満 (5-6)
        ServiceMaster(service_code='1341', service_name='地域通所介護３１', unit=657, stay_time_category='5-6', care_level='要介護1'),
        ServiceMaster(service_code='1342', service_name='地域通所介護３２', unit=776, stay_time_category='5-6', care_level='要介護2'),
        ServiceMaster(service_code='1343', service_name='地域通所介護３３', unit=895, stay_time_category='5-6', care_level='要介護3'),
        ServiceMaster(service_code='1344', service_name='地域通所介護３４', unit=1014, stay_time_category='5-6', care_level='要介護4'),
        ServiceMaster(service_code='1345', service_name='地域通所介護３５', unit=1134, stay_time_category='5-6', care_level='要介護5'),

        # 6時間以上7時間未満 (6-7)
        ServiceMaster(service_code='1346', service_name='地域通所介護４１', unit=678, stay_time_category='6-7', care_level='要介護1'),
        ServiceMaster(service_code='1347', service_name='地域通所介護４２', unit=801, stay_time_category='6-7', care_level='要介護2'),
        ServiceMaster(service_code='1348', service_name='地域通所介護４３', unit=925, stay_time_category='6-7', care_level='要介護3'),
        ServiceMaster(service_code='1349', service_name='地域通所介護４４', unit=1049, stay_time_category='6-7', care_level='要介護4'),
        ServiceMaster(service_code='1350', service_name='地域通所介護４５', unit=1172, stay_time_category='6-7', care_level='要介護5'),

        # 7時間以上8時間未満 (7-8)
        ServiceMaster(service_code='1441', service_name='地域通所介護５１', unit=783, stay_time_category='7-8', care_level='要介護1'),
        ServiceMaster(service_code='1442', service_name='地域通所介護５２', unit=925, stay_time_category='7-8', care_level='要介護2'),
        ServiceMaster(service_code='1443', service_name='地域通所介護５３', unit=1072, stay_time_category='7-8', care_level='要介護3'),
        ServiceMaster(service_code='1444', service_name='地域通所介護５４', unit=1220, stay_time_category='7-8', care_level='要介護4'),
        ServiceMaster(service_code='1445', service_name='地域通所介護５５', unit=1365, stay_time_category='7-8', care_level='要介護5'),

        # 8時間以上9時間未満 (8-9)
        ServiceMaster(service_code='1446', service_name='地域通所介護６１', unit=798, stay_time_category='8-9', care_level='要介護1'),
        ServiceMaster(service_code='1447', service_name='地域通所介護６２', unit=944, stay_time_category='8-9', care_level='要介護2'),
        ServiceMaster(service_code='1448', service_name='地域通所介護６３', unit=1093, stay_time_category='8-9', care_level='要介護3'),
        ServiceMaster(service_code='1449', service_name='地域通所介護６４', unit=1245, stay_time_category='8-9', care_level='要介護4'),
        ServiceMaster(service_code='1450', service_name='地域通所介護６５', unit=1396, stay_time_category='8-9', care_level='要介護5'),
    ]
    ServiceMaster.objects.bulk_create(a)
    messages.success(request, 'マスタデータの登録が完了しました')
    return redirect('dashboard:user_list')