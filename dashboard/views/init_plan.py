from dashboard.models import ServiceMaster
from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages

def init_plan(request):
    # ServiceMaster.objects.all().delete()
    # ServiceMaster.objects.bulk_create([
    #     # 地域密着型通所介護（種類コード：78）

    #     # 3時間以上4時間未満 (3-4)
    #     ServiceMaster(service_code='1141', service_name='地域通所介護１１', unit=416, stay_time_category='3-4', care_level='要介護1'),
    #     ServiceMaster(service_code='1142', service_name='地域通所介護１２', unit=478, stay_time_category='3-4', care_level='要介護2'),
    #     ServiceMaster(service_code='1143', service_name='地域通所介護１３', unit=540, stay_time_category='3-4', care_level='要介護3'),
    #     ServiceMaster(service_code='1144', service_name='地域通所介護１４', unit=600, stay_time_category='3-4', care_level='要介護4'),
    #     ServiceMaster(service_code='1145', service_name='地域通所介護１５', unit=663, stay_time_category='3-4', care_level='要介護5'),

    #     # 4時間以上5時間未満 (4-5)
    #     ServiceMaster(service_code='1241', service_name='地域通所介護２１', unit=436, stay_time_category='4-5', care_level='要介護1'),
    #     ServiceMaster(service_code='1242', service_name='地域通所介護２２', unit=501, stay_time_category='4-5', care_level='要介護2'),
    #     ServiceMaster(service_code='1243', service_name='地域通所介護２３', unit=566, stay_time_category='4-5', care_level='要介護3'),
    #     ServiceMaster(service_code='1244', service_name='地域通所介護２４', unit=631, stay_time_category='4-5', care_level='要介護4'),
    #     ServiceMaster(service_code='1245', service_name='地域通所介護２５', unit=696, stay_time_category='4-5', care_level='要介護5'),

    #     # 5時間以上6時間未満 (5-6)
    #     ServiceMaster(service_code='1341', service_name='地域通所介護３１', unit=657, stay_time_category='5-6', care_level='要介護1'),
    #     ServiceMaster(service_code='1342', service_name='地域通所介護３２', unit=776, stay_time_category='5-6', care_level='要介護2'),
    #     ServiceMaster(service_code='1343', service_name='地域通所介護３３', unit=895, stay_time_category='5-6', care_level='要介護3'),
    #     ServiceMaster(service_code='1344', service_name='地域通所介護３４', unit=1014, stay_time_category='5-6', care_level='要介護4'),
    #     ServiceMaster(service_code='1345', service_name='地域通所介護３５', unit=1134, stay_time_category='5-6', care_level='要介護5'),

    #     # 6時間以上7時間未満 (6-7)
    #     ServiceMaster(service_code='1346', service_name='地域通所介護４１', unit=678, stay_time_category='6-7', care_level='要介護1'),
    #     ServiceMaster(service_code='1347', service_name='地域通所介護４２', unit=801, stay_time_category='6-7', care_level='要介護2'),
    #     ServiceMaster(service_code='1348', service_name='地域通所介護４３', unit=925, stay_time_category='6-7', care_level='要介護3'),
    #     ServiceMaster(service_code='1349', service_name='地域通所介護４４', unit=1049, stay_time_category='6-7', care_level='要介護4'),
    #     ServiceMaster(service_code='1350', service_name='地域通所介護４５', unit=1172, stay_time_category='6-7', care_level='要介護5'),

    #     # 7時間以上8時間未満 (7-8)
    #     ServiceMaster(service_code='1441', service_name='地域通所介護５１', unit=783, stay_time_category='7-8', care_level='要介護1'),
    #     ServiceMaster(service_code='1442', service_name='地域通所介護５２', unit=925, stay_time_category='7-8', care_level='要介護2'),
    #     ServiceMaster(service_code='1443', service_name='地域通所介護５３', unit=1072, stay_time_category='7-8', care_level='要介護3'),
    #     ServiceMaster(service_code='1444', service_name='地域通所介護５４', unit=1220, stay_time_category='7-8', care_level='要介護4'),
    #     ServiceMaster(service_code='1445', service_name='地域通所介護５５', unit=1365, stay_time_category='7-8', care_level='要介護5'),

    #     # 8時間以上9時間未満 (8-9)
    #     ServiceMaster(service_code='1446', service_name='地域通所介護６１', unit=798, stay_time_category='8-9', care_level='要介護1'),
    #     ServiceMaster(service_code='1447', service_name='地域通所介護６２', unit=944, stay_time_category='8-9', care_level='要介護2'),
    #     ServiceMaster(service_code='1448', service_name='地域通所介護６３', unit=1093, stay_time_category='8-9', care_level='要介護3'),
    #     ServiceMaster(service_code='1449', service_name='地域通所介護６４', unit=1245, stay_time_category='8-9', care_level='要介護4'),
    #     ServiceMaster(service_code='1450', service_name='地域通所介護６５', unit=1396, stay_time_category='8-9', care_level='要介護5'),
    # ])
    messages.success(request, 'マスタデータの登録が完了しました')
    return redirect('dashboard:user_list')