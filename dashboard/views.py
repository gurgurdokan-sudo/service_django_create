from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from .models import User, ServiceMaster, ServicePlan, AddOnService
from .excel.service_sheet import create_service_sheet
from .forms import UserForm, PlanForm
from datetime import datetime
import json
from .calendar_table import get_month_days
#利用者一覧
def user_list(request):
    users = User.objects.all()
    for user in users:
        user.has_plan = ServicePlan.objects.filter(user=user).first() is not None
    return render(request, 'dashboard/user_list.html', {'users': users})
#新規作成
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'新規登録完了しました')
            return redirect('dashboard:user_list')
    else:
        form = UserForm()
    return render(request,'dashboard/user_form.html', {'form': form})
#Plan作成
def create_plan(request,user_id):
    if request.method == 'POST':
        form = PlanForm(request.POST,user_id=user_id)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user_id = user_id
            stay_cat = plan.stay_time_category
            service_sq = ServiceMaster.objects.filter(
                care_level = plan.user.care_level,
                stay_time_category = stay_cat
            )
            service = service_sq.first() if service_sq else None
            if service:
                plan.service_name = service.service_name
                plan.service_code = service.service_code
                plan.unit = service.unit
            form.save()
            messages.success(request,'プランを作成しました')
            return redirect('dashboard:service',user_id=user_id)
    else:
        form = PlanForm()
    return render(request,'dashboard/create_plan.html', {'form': form})
#Excel出力
def export_service_sheet(request, user_id, year, month):
    user = User.objects.get(id=user_id)
    wb = create_service_sheet(user, year, month)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="【様式】サービス提供票・別表"'

    wb.save(f'サービス提供表_{user.name}_{year}_{month}.xlsx')
    return response
#更新
def user_update(request, user_id):
    user = get_object_or_404(User,id=user_id)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request,f'{user.name}さんを更新されました')
            return redirect('dashboard:user_list')
    else:
        form = UserForm(instance=user)
    return render(request, 'dashboard/user_form.html', {'form': form})
#詳細
def user_detail(request,user_id):
    target = get_object_or_404(User,id=user_id)
    labels = {f.name: f.verbose_name for f in target._meta.fields}
    return render(request,'dashboard/user_detail.html',{'user': target,'labels': labels,})
#消去
def user_delete(request,user_id):
    target = get_object_or_404(User,id=user_id)
    if request.method=='POST':
        messages.error(request,f'{target.name}さんを消去しました')
        target.delete()
        return redirect('dashboard:user_list')
    return render(request,'dashboard/user_delete.html',{'user':target})
#サービス提供票
def user_service(request,user_id):
    target = get_object_or_404(User,id=user_id)
    plans = ServicePlan.objects.filter(user=target)
    for plan in plans:
        plan.schedule_json = json.dumps(plan.schedule_json)
        plan.actual_json = json.dumps(plan.actual_json)
    service = ServiceMaster.objects.all()
    service = service.filter(care_level = target.care_level)
    calendar = get_month_days(2026,3) #todo:月は動的に
    context = {
        'user': target,
        'plans': plans,
        'service': service,
        'calendar': calendar,
        'addon_service': AddOnService.objects.all(),
    }
    return render(request,'dashboard/user_service.html',context)

def init_plan(request):
    # AddOnService.objects.all().delete()
    # services = [
    #     AddOnService(code='0', service_name='値引き', price=-1000, unit=1, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='0', service_name='時間サービス', price=1000, unit=1, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='0', service_name='昼食代', price=690, unit=1, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
    #     AddOnService(code='0', service_name='おやつ代', price=150, unit=1, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
    #     AddOnService(code='0', service_name='洗濯代', price=120, unit=1, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
    #     AddOnService(code='0', service_name='教養娯楽費', price=50, unit=1, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
    #     AddOnService(code='0', service_name='パット代', price=100, unit=1, category='消耗品', is_tax=True, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='0', service_name='キャンセル料', price=1000, unit=1, category='自費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='0', service_name='昼食代B', price=500, unit=1, category='食費', is_tax=True, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
    #     AddOnService(code='0', service_name='夕食代', price=690, unit=1, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
    #     AddOnService(code='0', service_name='時間サービス', price=1500, unit=1, category='自費', is_tax=True, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='0', service_name='宿泊費', price=6800, unit=1, category='宿泊', is_tax=True, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='0', service_name='宿泊費B', price=3500, unit=1, category='宿泊', is_tax=True, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='901', service_name='夕食代', price=690, unit=1, category='食費', is_tax=True, insurance_type='self_pay', apply_unit='per_day', medical_deduction=False),
    #     AddOnService(code='902', service_name='捕食', price=150, unit=1, category='食費', is_tax=False, insurance_type='self_pay', apply_unit='per_service', medical_deduction=False),
    #     AddOnService(code='6107', service_name='通所介護処遇改善加算Ⅱ', unit=0, category='通所介護',insurance_type='insurance',apply_unit='monthly'),
    #     # 延長・感染症・災害（所定単位数に対する％加算・減算は単位を0として登録）
    #     AddOnService(code='6600', service_name='通所介護感染症災害3％加算', unit=0, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6601', service_name='通所介護延長加算1', unit=50, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6602', service_name='通所介護延長加算2', unit=100, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6603', service_name='通所介護延長加算3', unit=150, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6604', service_name='通所介護延長加算4', unit=200, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6605', service_name='通所介護延長加算5', unit=250, category='通所介護', insurance_type='insurance', apply_unit='per_service'),

    #     # 共生型サービス減算（％減算のため単位0）
    #     AddOnService(code='6364', service_name='通所介護共生型サービス生活介護', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='6365', service_name='通所介護共生型サービス自立訓練', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='6366', service_name='通所介護共生型サービス児童発達支援', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='6367', service_name='通所介護共生型サービス放課後等デイ', unit=0, category='通所介護', insurance_type='insurance', apply_unit='monthly'),

    #     # 基本加算・入浴・中重度
    #     AddOnService(code='6350', service_name='通所介護生活相談員配置等加算', unit=13, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='8110', service_name='通所介護中山間地域等提供加算', unit=0, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='5301', service_name='通所介護入浴介助加算Ⅰ', unit=40, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='5303', service_name='通所介護入浴介助加算Ⅱ', unit=55, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='5306', service_name='通所介護中重度者ケア体制加算', unit=45, category='通所介護', insurance_type='insurance', apply_unit='per_day'),

    #     # 生活機能向上・個別機能訓練
    #     AddOnService(code='4001', service_name='通所介護生活機能向上連携加算Ⅰ', unit=100, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='4002', service_name='通所介護生活機能向上連携加算Ⅱ1', unit=200, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='4003', service_name='通所介護生活機能向上連携加算Ⅱ2', unit=100, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='5051', service_name='通所介護個別機能訓練加算Ⅰ1', unit=56, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='5053', service_name='通所介護個別機能訓練加算Ⅰ2', unit=76, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='5052', service_name='通所介護個別機能訓練加算Ⅱ', unit=20, category='通所介護', insurance_type='insurance', apply_unit='monthly'),

    #     # ADL・認知症・若年性
    #     AddOnService(code='6338', service_name='通所介護ADL維持等加算Ⅰ', unit=30, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='6339', service_name='通所介護ADL維持等加算Ⅱ', unit=60, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='5305', service_name='通所介護認知症加算', unit=60, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='6109', service_name='通所介護若年性認知症受入加算', unit=60, category='通所介護', insurance_type='insurance', apply_unit='per_day'),

    #     # 栄養・口腔・科学的介護
    #     AddOnService(code='6116', service_name='通所介護栄養アセスメント加算', unit=50, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='5605', service_name='通所介護栄養改善加算', unit=200, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='6202', service_name='通所介護口腔栄養スクリーニング加算Ⅰ', unit=20, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6201', service_name='通所介護口腔栄養スクリーニング加算Ⅱ', unit=5, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='5606', service_name='通所介護口腔機能向上加算Ⅰ', unit=150, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='5608', service_name='通所介護口腔機能向上加算Ⅱ', unit=160, category='通所介護', insurance_type='insurance', apply_unit='monthly'),
    #     AddOnService(code='6361', service_name='通所介護科学的介護推進体制加算', unit=40, category='通所介護', insurance_type='insurance', apply_unit='monthly'),

    #     # 減算
    #     AddOnService(code='5611', service_name='通所介護同一建物減算', unit=-94, category='通所介護', insurance_type='insurance', apply_unit='per_day'),
    #     AddOnService(code='5612', service_name='通所介護送迎減算', unit=-47, category='通所介護', insurance_type='insurance', apply_unit='per_service'),

    #     # サービス提供体制加算
    #     AddOnService(code='6099', service_name='通所介護サービス提供体制加算Ⅰ', unit=22, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6100', service_name='通所介護サービス提供体制加算Ⅱ', unit=18, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    #     AddOnService(code='6102', service_name='通所介護サービス提供体制加算Ⅲ', unit=6, category='通所介護', insurance_type='insurance', apply_unit='per_service'),
    # ]

    # AddOnService.objects.bulk_create(services)
    #     # 2時間以上3時間未満 (<3)
    #     ServiceMaster(service_code='2141', service_name='通所介護21・時減', unit=272, stay_time_category='<3', care_level='要介護1'),
    #     ServiceMaster(service_code='2142', service_name='通所介護22・時減', unit=311, stay_time_category='<3', care_level='要介護2'),
    #     ServiceMaster(service_code='2143', service_name='通所介護23・時減', unit=351, stay_time_category='<3', care_level='要介護3'),
    #     ServiceMaster(service_code='2144', service_name='通所介護24・時減', unit=392, stay_time_category='<3', care_level='要介護4'),
    #     ServiceMaster(service_code='2145', service_name='通所介護25・時減', unit=432, stay_time_category='<3', care_level='要介護5'),

    #     # 3時間以上4時間未満 (3-4)
    #     ServiceMaster(service_code='2241', service_name='通所介護11', unit=370, stay_time_category='3-4', care_level='要介護1'),
    #     ServiceMaster(service_code='2242', service_name='通所介護12', unit=423, stay_time_category='3-4', care_level='要介護2'),
    #     ServiceMaster(service_code='2243', service_name='通所介護13', unit=479, stay_time_category='3-4', care_level='要介護3'),
    #     ServiceMaster(service_code='2244', service_name='通所介護14', unit=533, stay_time_category='3-4', care_level='要介護4'),
    #     ServiceMaster(service_code='2245', service_name='通所介護15', unit=588, stay_time_category='3-4', care_level='要介護5'),

    #     # 4時間以上5時間未満 (4-5)
    #     ServiceMaster(service_code='2246', service_name='通所介護21', unit=388, stay_time_category='4-5', care_level='要介護1'),
    #     ServiceMaster(service_code='2247', service_name='通所介護22', unit=444, stay_time_category='4-5', care_level='要介護2'),
    #     ServiceMaster(service_code='2248', service_name='通所介護23', unit=502, stay_time_category='4-5', care_level='要介護3'),
    #     ServiceMaster(service_code='2249', service_name='通所介護24', unit=560, stay_time_category='4-5', care_level='要介護4'),
    #     ServiceMaster(service_code='2250', service_name='通所介護25', unit=617, stay_time_category='4-5', care_level='要介護5'),

    #     # 5時間以上6時間未満 (5-6)
    #     ServiceMaster(service_code='2341', service_name='通所介護31', unit=570, stay_time_category='5-6', care_level='要介護1'),
    #     ServiceMaster(service_code='2342', service_name='通所介護32', unit=673, stay_time_category='5-6', care_level='要介護2'),
    #     ServiceMaster(service_code='2343', service_name='通所介護33', unit=777, stay_time_category='5-6', care_level='要介護3'),
    #     ServiceMaster(service_code='2344', service_name='通所介護34', unit=880, stay_time_category='5-6', care_level='要介護4'),
    #     ServiceMaster(service_code='2345', service_name='通所介護35', unit=984, stay_time_category='5-6', care_level='要介護5'),

    #     # 6時間以上7時間未満 (6-7)
    #     ServiceMaster(service_code='2346', service_name='通所介護41', unit=584, stay_time_category='6-7', care_level='要介護1'),
    #     ServiceMaster(service_code='2347', service_name='通所介護42', unit=689, stay_time_category='6-7', care_level='要介護2'),
    #     ServiceMaster(service_code='2348', service_name='通所介護43', unit=796, stay_time_category='6-7', care_level='要介護3'),
    #     ServiceMaster(service_code='2349', service_name='通所介護44', unit=901, stay_time_category='6-7', care_level='要介護4'),
    #     ServiceMaster(service_code='2350', service_name='通所介護45', unit=1008, stay_time_category='6-7', care_level='要介護5'),

    #     # 7時間以上8時間未満 (7-8)
    #     ServiceMaster(service_code='2441', service_name='通所介護51', unit=658, stay_time_category='7-8', care_level='要介護1'),
    #     ServiceMaster(service_code='2442', service_name='通所介護52', unit=777, stay_time_category='7-8', care_level='要介護2'),
    #     ServiceMaster(service_code='2443', service_name='通所介護53', unit=900, stay_time_category='7-8', care_level='要介護3'),
    #     ServiceMaster(service_code='2444', service_name='通所介護54', unit=1023, stay_time_category='7-8', care_level='要介護4'),
    #     ServiceMaster(service_code='2445', service_name='通所介護55', unit=1148, stay_time_category='7-8', care_level='要介護5'),

    #     # 8時間以上9時間未満 (8-9)
    #     ServiceMaster(service_code='2446', service_name='通所介護61', unit=669, stay_time_category='8-9', care_level='要介護1'),
    #     ServiceMaster(service_code='2447', service_name='通所介護62', unit=791, stay_time_category='8-9', care_level='要介護2'),
    #     ServiceMaster(service_code='2448', service_name='通所介護63', unit=915, stay_time_category='8-9', care_level='要介護3'),
    #     ServiceMaster(service_code='2449', service_name='通所介護64', unit=1041, stay_time_category='8-9', care_level='要介護4'),
    #     ServiceMaster(service_code='2450', service_name='通所介護65', unit=1168, stay_time_category='8-9', care_level='要介護5'),
    # ]

    # ServiceMaster.objects.bulk_create(services)
    return render(request, 'dashboard/base/test.html', {'message': 'マスタデータの登録が完了しました'})
#サービス提供の保存
def save_service(request,user_id):
    target = get_object_or_404(User,id=user_id)
    plan = ServicePlan.objects.filter(user=target).first()
    if request.method =='POST':
        print('------------------保存処理開始------------------')
        schedule_json = request.POST.get('schedule_json')
        print('schedule_json:', schedule_json)
        actual_json = request.POST.get('actual_json')
        if schedule_json and actual_json:
            plan.schedule_json = json.loads(schedule_json)
            plan.actual_json = json.loads(actual_json)
            plan.save()
            messages.success(request,'サービス提供内容を保存しました')
            return redirect('dashboard:user_list') 
        add_on_services = request.POST.get('selected_service')
        add_on_id = add_on_services.replace('addon_','') if add_on_services else None
        if add_on_id:
            add_on_service = get_object_or_404(AddOnService, id=add_on_id)
            print('選択された追加サービス:', add_on_service.service_name)
            messages.success(request,f'追加サービスを保存しました: {add_on_service.service_name}')
            return redirect('dashboard:service', user_id=user_id)
    return render(request,'dashboard/user_list.html')