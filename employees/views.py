from datetime import date as date_cls

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AssignmentForm, EmployeeForm
from .models import Assignment, Attendance, Employee


# 従業員一覧
def employee_list(request):
    employees = Employee.objects.filter(is_superuser=False).order_by('-is_active', 'username')
    return render(request, 'employees/employee_list.html', {'employees': employees})


def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('employees:employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'employees/employee_form.html', {'form': form, 'title': '従業員の新規登録'})


def employee_update(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('employees:employee_list')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'employees/employee_form.html', {'form': form, 'title': '従業員情報の更新'})


def employee_delete(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
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
    })


def assignment_create(request):
    initial_date = _parse_date(request.GET.get('date')) or timezone.localdate()
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save()
            return redirect(f"{_assignment_list_url()}?date={assignment.date.isoformat()}")
    else:
        form = AssignmentForm(initial={'date': initial_date})
    return render(request, 'employees/assignment_form.html', {'form': form, 'title': '担当スケジュールの登録'})


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


def _parse_date(value):
    if not value:
        return None
    try:
        return date_cls.fromisoformat(value)
    except ValueError:
        return None


def _assignment_list_url():
    from django.urls import reverse
    return reverse('employees:assignment_list')
