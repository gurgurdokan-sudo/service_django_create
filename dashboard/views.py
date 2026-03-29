from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from .models import User, ServiceMaster, ServicePlan
from .excel.service_sheet import create_service_sheet
from .forms import UserForm, PlanForm
from datetime import datetime
import json
from .calendar_table import get_month_days
#利用者一覧
def user_list(request):
    users = User.objects.all()
    for user in users:
        user.has_plan = ServicePlan.objects.filter(user=user).exists()
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

    wb.save(response)
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
    plan = ServicePlan.objects.get(user=target)
    service = ServiceMaster.objects.all()
    service = service.filter(care_level = target.care_level)
    sq = ServiceMaster.get_quer_plan(level=target.care_level,stay_time_category = plan.stay_time_category)
    naiyou = sq.first() if sq else None
    calendar = get_month_days(2026,3) #todo:月は動的に
    context = {
        'user': target,
        'plan': plan,
        'service': service,
        'naiyou':naiyou,
        'calendar': calendar,
        'schedule_json': json.dumps(plan.schedule_json),
        'actual_json': json.dumps(plan.actual_json),
    }
    return render(request,'dashboard/user_service.html',context)
from django.shortcuts import render
from .models import ServiceMaster

def init_plan(request):
    services = [
        # 2時間以上3時間未満 (<3)
        ServiceMaster(service_code='2141', service_name='通所介護21・時減', unit=272, stay_time_category='<3', care_level='要介護1'),
        ServiceMaster(service_code='2142', service_name='通所介護22・時減', unit=311, stay_time_category='<3', care_level='要介護2'),
        ServiceMaster(service_code='2143', service_name='通所介護23・時減', unit=351, stay_time_category='<3', care_level='要介護3'),
        ServiceMaster(service_code='2144', service_name='通所介護24・時減', unit=392, stay_time_category='<3', care_level='要介護4'),
        ServiceMaster(service_code='2145', service_name='通所介護25・時減', unit=432, stay_time_category='<3', care_level='要介護5'),

        # 3時間以上4時間未満 (3-4)
        ServiceMaster(service_code='2241', service_name='通所介護11', unit=370, stay_time_category='3-4', care_level='要介護1'),
        ServiceMaster(service_code='2242', service_name='通所介護12', unit=423, stay_time_category='3-4', care_level='要介護2'),
        ServiceMaster(service_code='2243', service_name='通所介護13', unit=479, stay_time_category='3-4', care_level='要介護3'),
        ServiceMaster(service_code='2244', service_name='通所介護14', unit=533, stay_time_category='3-4', care_level='要介護4'),
        ServiceMaster(service_code='2245', service_name='通所介護15', unit=588, stay_time_category='3-4', care_level='要介護5'),

        # 4時間以上5時間未満 (4-5)
        ServiceMaster(service_code='2246', service_name='通所介護21', unit=388, stay_time_category='4-5', care_level='要介護1'),
        ServiceMaster(service_code='2247', service_name='通所介護22', unit=444, stay_time_category='4-5', care_level='要介護2'),
        ServiceMaster(service_code='2248', service_name='通所介護23', unit=502, stay_time_category='4-5', care_level='要介護3'),
        ServiceMaster(service_code='2249', service_name='通所介護24', unit=560, stay_time_category='4-5', care_level='要介護4'),
        ServiceMaster(service_code='2250', service_name='通所介護25', unit=617, stay_time_category='4-5', care_level='要介護5'),

        # 5時間以上6時間未満 (5-6)
        ServiceMaster(service_code='2341', service_name='通所介護31', unit=570, stay_time_category='5-6', care_level='要介護1'),
        ServiceMaster(service_code='2342', service_name='通所介護32', unit=673, stay_time_category='5-6', care_level='要介護2'),
        ServiceMaster(service_code='2343', service_name='通所介護33', unit=777, stay_time_category='5-6', care_level='要介護3'),
        ServiceMaster(service_code='2344', service_name='通所介護34', unit=880, stay_time_category='5-6', care_level='要介護4'),
        ServiceMaster(service_code='2345', service_name='通所介護35', unit=984, stay_time_category='5-6', care_level='要介護5'),

        # 6時間以上7時間未満 (6-7)
        ServiceMaster(service_code='2346', service_name='通所介護41', unit=584, stay_time_category='6-7', care_level='要介護1'),
        ServiceMaster(service_code='2347', service_name='通所介護42', unit=689, stay_time_category='6-7', care_level='要介護2'),
        ServiceMaster(service_code='2348', service_name='通所介護43', unit=796, stay_time_category='6-7', care_level='要介護3'),
        ServiceMaster(service_code='2349', service_name='通所介護44', unit=901, stay_time_category='6-7', care_level='要介護4'),
        ServiceMaster(service_code='2350', service_name='通所介護45', unit=1008, stay_time_category='6-7', care_level='要介護5'),

        # 7時間以上8時間未満 (7-8)
        ServiceMaster(service_code='2441', service_name='通所介護51', unit=658, stay_time_category='7-8', care_level='要介護1'),
        ServiceMaster(service_code='2442', service_name='通所介護52', unit=777, stay_time_category='7-8', care_level='要介護2'),
        ServiceMaster(service_code='2443', service_name='通所介護53', unit=900, stay_time_category='7-8', care_level='要介護3'),
        ServiceMaster(service_code='2444', service_name='通所介護54', unit=1023, stay_time_category='7-8', care_level='要介護4'),
        ServiceMaster(service_code='2445', service_name='通所介護55', unit=1148, stay_time_category='7-8', care_level='要介護5'),

        # 8時間以上9時間未満 (8-9)
        ServiceMaster(service_code='2446', service_name='通所介護61', unit=669, stay_time_category='8-9', care_level='要介護1'),
        ServiceMaster(service_code='2447', service_name='通所介護62', unit=791, stay_time_category='8-9', care_level='要介護2'),
        ServiceMaster(service_code='2448', service_name='通所介護63', unit=915, stay_time_category='8-9', care_level='要介護3'),
        ServiceMaster(service_code='2449', service_name='通所介護64', unit=1041, stay_time_category='8-9', care_level='要介護4'),
        ServiceMaster(service_code='2450', service_name='通所介護65', unit=1168, stay_time_category='8-9', care_level='要介護5'),
    ]

    # bulk_createで一括保存
    ServiceMaster.objects.bulk_create(services)
    return render(request, 'dashboard/base/test.html', {'message': 'マスタデータの登録が完了しました'})
#サービス提供の保存
def save_service(request,user_id):
    if request.method =='POST':
        print('------------------保存処理開始------------------')
        print('schedule_json:', schedule_json)
        print(plan.schedule_json)
        schedule_json = request.POST.get('schedule_json')
        actual_json = request.POST.get('actual_json')
        target = get_object_or_404(User,id=user_id)
        plan = ServicePlan.objects.get(user=target)
        plan.schedule_json = json.loads(schedule_json)
        plan.actual_json = json.loads(actual_json)
        plan.save()
        messages.success(request,'サービス提供内容を保存しました')
        return redirect('dashboard:user_list')
    return render(request,'dashboard/user_list.html')