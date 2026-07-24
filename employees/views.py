from datetime import date as date_cls, datetime, timedelta
from pykakasi import kakasi
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.models import ServicePlan
from diary.models import Entry

from .forms import AssignmentForm, StaffForm, StaffUpdateForm, ShiftPatternForm
from .permissions import delete_permission_required
from .models import Assignment, Attendance, Staff, ShiftPattern


# 従業員一覧
def employee_list(request):
    employees = Staff.objects.filter(is_superuser=False).order_by('-is_active', 'username')
    return render(request, 'employees/employee_list.html', {'employees': employees})


def employee_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)

            kks = kakasi()
            conv = kks.convert(f"{obj.last_name} {obj.first_name}")

            # ローマ字だけ抽出
            ascii_name = "".join([c['hepburn'] for c in conv]).lower()

            # 重複チェック
            base = ascii_name.replace(' ','')
            i = 1
            while Staff.objects.filter(username=ascii_name).exists():
                ascii_name = f"{base}{i}"
                i += 1

            obj.username = ascii_name
            obj.save()
            return redirect('employees:employee_list')
    else:
        form = StaffForm()
    return render(request, 'employees/employee_form.html', {'form': form, 'title': '従業員の新規登録'})


def employee_update(request, employee_id):
    employee = get_object_or_404(Staff, id=employee_id)
    if request.method == 'POST':
        form = StaffUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('employees:employee_list')
    else:
        form = StaffForm(instance=employee)
    return render(request, 'employees/employee_form.html', {'form': form, 'title': '従業員情報の更新'})


@delete_permission_required
def employee_delete(request, employee_id):
    employee = get_object_or_404(Staff, id=employee_id)
    if request.method == 'POST':
        employee.delete()
        return redirect('employees:employee_list')
    return render(request, 'employees/employee_delete.html', {'employee': employee})


# 担当スケジュール（日付ごとの従業員×利用者の割当て）
def assignment_list(request):
    target_date = _parse_date(request.GET.get('date')) or timezone.localdate()
    assignments = (
        Assignment.objects.filter(date=target_date)
        .select_related('employee', 'user')
        .order_by('employee__username')
    )
    return render(request, 'employees/assignment_list.html', {
        'assignments': assignments,
        'target_date': target_date,
        'prev_date': target_date - timedelta(days=1),
        'next_date': target_date + timedelta(days=1),
    })


def assignment_create(request):
    initial_date = _parse_date(request.GET.get('date')) or timezone.localdate()
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save()
            # 「毎週◯曜日にシフトパターン登録しますか？」ポップアップでOKした場合
            if request.POST.get('register_pattern'):
                _, created = ShiftPattern.objects.get_or_create(
                    employee=assignment.employee, user=assignment.user,
                    weekday=assignment.date.weekday(),
                    defaults={
                        'start_time': assignment.start_time,
                        'end_time': assignment.end_time,
                        'is_daily_reporter': assignment.is_daily_reporter,
                    },
                )
                if created:
                    messages.success(request, 'シフトパターンにも登録しました。')
            return redirect(f"{_assignment_list_url()}?date={assignment.date.isoformat()}")
    else:
        form = AssignmentForm(initial={'date': initial_date})
    return render(request, 'employees/assignment_form.html', {'form': form, 'title': '担当スケジュールの登録'})


@delete_permission_required
def assignment_delete(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        target_date = assignment.date
        assignment.delete()
        return redirect(f"{_assignment_list_url()}?date={target_date.isoformat()}")
    return render(request, 'employees/assignment_delete.html', {'assignment': assignment})


# 出退勤記録（Slackボタンからの打刻を閲覧する画面）
def attendance_list(request):
    target_date = _parse_date(request.GET.get('date')) or timezone.localdate()
    records = (
        Attendance.objects.filter(date=target_date)
        .select_related('employee')
        .order_by('employee__username', 'kind')
    )
    return render(request, 'employees/attendance_list.html', {
        'records': records,
        'target_date': target_date,
    })


# カレンダー（利用者=終日イベント、スタッフ担当=時間帯イベント）
def calendar_view(request):
    from dashboard.models import User
    today = timezone.localdate()
    return render(request, 'employees/calendar.html', {
        'this_year': today.year,
        'this_month': today.month,
        # ポップアップ（シフト追加/編集モーダル）の選択肢
        'staff_options': Staff.objects.filter(is_active=True, is_superuser=False)
                                         .order_by('username'),
        'care_user_options': User.objects.all().order_by('name_kana'),
    })


def calendar_events(request):
    '''FullCalendar用のイベントJSON。start/endはISO形式で渡される'''
    start = _parse_date((request.GET.get('start') or '')[:10])
    end = _parse_date((request.GET.get('end') or '')[:10])
    if not start or not end:
        return JsonResponse([], safe=False)

    events = []

    # 利用者の来所予定（サービス提供票の予定から終日イベントで表示）
    months = _months_between(start, end)
    plans = ServicePlan.objects.none()
    for year, month in months:
        plans = plans | ServicePlan.objects.filter(year=year, month=month)
    for plan in plans.select_related('user'):
        for day_str, value in (plan.schedule_json or {}).items():
            if value != '1':
                continue
            try:
                target = date_cls(plan.year, plan.month, int(day_str))
            except ValueError:
                continue
            if not (start <= target < end):
                continue
            events.append({
                'title': f'{plan.user.name} {plan.start_time:%H:%M}〜{plan.end_time:%H:%M}',
                'start': target.isoformat(),
                'allDay': True,
                'color': '#5b7c99',
            })

    # スタッフの担当（時間帯イベント。文字はスタッフ名のみ、人ごとに色分け）
    assignments = (
        Assignment.objects.filter(date__gte=start, date__lt=end)
        .select_related('employee', 'user')
    )
    for a in assignments:
        title = str(a.employee)
        if a.is_daily_reporter:
            title += ' 📝'
        event = {
            'id': f'assignment-{a.id}',
            'title': title,
            'color': _employee_color(a.employee_id),
            'extendedProps': {
                'assignmentId': a.id,
                'employeeId': a.employee_id,
                'userId': a.user_id,
                'userName': a.user.name,
                'date': a.date.isoformat(),
                'startTime': a.start_time.strftime('%H:%M') if a.start_time else '',
                'endTime': a.end_time.strftime('%H:%M') if a.end_time else '',
                'isDailyReporter': a.is_daily_reporter,
                'note': a.note,
            },
        }
        if a.start_time and a.end_time:
            event['start'] = datetime.combine(a.date, a.start_time).isoformat()
            event['end'] = datetime.combine(a.date, a.end_time).isoformat()
            event['classNames'] = ['custom-width']
        else:
            event['start'] = a.date.isoformat()
            event['allDay'] = True
        events.append(event)

    return JsonResponse(events, safe=False)


# スタッフごとのイベント色（同時間帯の重なりを人で見分けるため）
EMPLOYEE_COLORS = [
    '#2e7d32', '#c62828', '#6a1b9a', '#ef6c00',
    '#00838f', '#5d4037', '#37474f', '#d81b60',
]


def _employee_color(employee_id):
    return EMPLOYEE_COLORS[employee_id % len(EMPLOYEE_COLORS)]


@require_POST
def shift_generate(request):
    '''シフトパターンを指定月のAssignmentに一括展開する'''
    try:
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
    except (TypeError, ValueError):
        messages.error(request, '対象の年月が不正です')
        return redirect('employees:calendar')
    created = ShiftPattern.generate_assignments(year, month)
    messages.success(request, f'{year}年{month}月のシフトを生成しました（新規 {created} 件）')
    return redirect('employees:calendar')


# シフトパターン（いつも通りのシフトの型）
# セレクターで選んだスタッフの曜日別シフトを表示する
def pattern_list(request):
    staff = Staff.objects.filter(is_active=True, is_superuser=False).order_by('username')
    selected = None
    employee_id = request.GET.get('employee')
    if employee_id:
        selected = staff.filter(id=employee_id).first()
    if selected is None:
        selected = staff.first()

    patterns = (
        ShiftPattern.objects.filter(employee=selected)
        .select_related('user')
        .order_by('weekday', 'start_time')
    ) if selected else ShiftPattern.objects.none()

    # 曜日ごとにまとめる（月〜日、パターンが無い曜日も行として出す）
    from .models import WEEKDAY_CHOICES
    by_weekday = [
        {'weekday': value, 'label': label,
         'patterns': [p for p in patterns if p.weekday == value]}
        for value, label in WEEKDAY_CHOICES
    ]

    return render(request, 'employees/pattern_list.html', {
        'staff': staff,
        'selected': selected,
        'by_weekday': by_weekday,
    })


def _pattern_list_url(employee_id=None):
    from django.urls import reverse
    url = reverse('employees:pattern_list')
    return f'{url}?employee={employee_id}' if employee_id else url


def pattern_create(request):
    if request.method == 'POST':
        form = ShiftPatternForm(request.POST)
        if form.is_valid():
            pattern = form.save()  # 新規は常に有効（is_activeのデフォルト=True）
            return redirect(_pattern_list_url(pattern.employee_id))
    else:
        # 一覧で選択中だったスタッフを初期値にする
        form = ShiftPatternForm(initial={'employee': request.GET.get('employee')})
    return render(request, 'employees/pattern_form.html', {'form': form, 'title': 'シフトパターンの登録'})


def pattern_update(request, pattern_id):
    pattern = get_object_or_404(ShiftPattern, id=pattern_id)
    if request.method == 'POST':
        form = ShiftPatternForm(request.POST, instance=pattern)
        if form.is_valid():
            form.save()
            return redirect(_pattern_list_url(pattern.employee_id))
    else:
        form = ShiftPatternForm(instance=pattern)
    return render(request, 'employees/pattern_form.html', {'form': form, 'title': 'シフトパターンの更新'})


@delete_permission_required
def pattern_delete(request, pattern_id):
    pattern = get_object_or_404(ShiftPattern, id=pattern_id)
    if request.method == 'POST':
        employee_id = pattern.employee_id
        pattern.delete()
        return redirect(_pattern_list_url(employee_id))
    return render(request, 'employees/pattern_delete.html', {'pattern': pattern})


# 日報の未提出一覧（日報担当なのにその日のEntryが無いもの）
def unsubmitted_reports(request):
    today = timezone.localdate()
    start = _parse_date(request.GET.get('from')) or today.replace(day=1)
    end = _parse_date(request.GET.get('to')) or today
    targets = (
        Assignment.objects.filter(
            is_daily_reporter=True, date__gte=start, date__lte=end,
        )
        .select_related('employee', 'user')
        .order_by('date', 'employee_id')
    )
    unsubmitted = [
        a for a in targets
        if not Entry.objects.filter(user=a.user, date=a.date).exists()
    ]
    return render(request, 'employees/unsubmitted_list.html', {
        'unsubmitted': unsubmitted,
        'from_date': start,
        'to_date': end,
    })


def _parse_date(value):
    if not value:
        return None
    try:
        return date_cls.fromisoformat(value)
    except ValueError:
        return None


def _months_between(start, end):
    '''startからendまでに含まれる (year, month) の一覧'''
    months = []
    cursor = start.replace(day=1)
    while cursor < end:
        months.append((cursor.year, cursor.month))
        cursor = (cursor + timedelta(days=32)).replace(day=1)
    return months


def _assignment_list_url():
    from django.urls import reverse
    return reverse('employees:assignment_list')


# ログイン（superuserは管理サイトへ、スタッフは業務画面へ振り分ける）
from django.contrib.auth.views import LoginView


class StaffLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        if self.request.user.is_superuser:
            return '/admin/'
        return super().get_success_url()
